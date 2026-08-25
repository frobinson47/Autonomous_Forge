"""Lock file guarding concurrent forge run/pipeline invocations.

Prevents two concurrent `forge run`/`forge pipeline` processes against the
same repo from racing each other (e.g. a human and an agent, or two agent
sessions, running against the same repo at once). A stale lock — one whose
recorded process is no longer alive — is detected and cleared automatically
rather than requiring manual cleanup.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

LOCK_RELATIVE_PATH = Path(".forge") / ".lock"


class LockHeldError(RuntimeError):
    """Raised when a live lock is already held by another process."""

    def __init__(self, pid: int, acquired_at: str):
        self.pid = pid
        self.acquired_at = acquired_at
        super().__init__(f"already running (pid {pid}, since {acquired_at})")


def _pid_alive(pid: int) -> bool:
    """Check whether a process with the given PID is currently running.

    On POSIX, ``os.kill(pid, 0)`` is the standard liveness probe. On
    Windows it is not safe to use for this: passing signal 0 there maps to
    ``TerminateProcess(handle, 0)``, which actually kills the process
    instead of merely probing it. So Windows uses ``OpenProcess`` via
    ctypes instead, which only queries.
    """
    if sys.platform == "win32":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(  # type: ignore[attr-defined]
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[attr-defined]
            return True
        return False

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we can't signal it — still alive.
        return True
    return True


@dataclass
class ForgeLock:
    """A held lock. Call release() when the guarded work is done."""

    root: Path
    path: Path

    def release(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    def __enter__(self) -> "ForgeLock":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()


def _read_lock(path: Path) -> tuple[int | None, str]:
    """Read a lock file's recorded pid and timestamp, or (None, "unknown") if unreadable."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return int(data["pid"]), str(data.get("acquired_at", "unknown"))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None, "unknown"


_MAX_ACQUIRE_ATTEMPTS = 3


def acquire_lock(root: Path = Path("."), timestamp: str | None = None) -> ForgeLock:
    """Acquire the forge run/pipeline lock for ``root``.

    A stale lock (recorded PID no longer alive, or the lock file is
    unreadable/malformed) is cleared automatically before acquiring.
    Raises LockHeldError if a live lock is already held by another process.

    Acquisition is atomic end-to-end: the payload is written in full to a
    private temp file first, then published to the lock path via
    ``os.link`` — which, like ``O_CREAT | O_EXCL``, fails with
    ``FileExistsError`` if the destination already exists, so two processes
    racing to acquire at the same instant can never both succeed. Unlike a
    bare ``open(O_CREAT | O_EXCL)`` followed by a separate write, there is
    no window where a racer can observe a lock file that exists but isn't
    fully written yet — every lock file this function ever creates is
    complete before it becomes visible at the lock path. (AUTO-070: an
    earlier version of this function had exactly that window — a second
    racer could read the not-yet-written file, fail to parse it, conclude
    "no valid lock, safe to delete," and steal it out from under the first
    racer, letting both report success. Caught by
    `test_concurrent_acquire_never_succeeds_twice` on a real CI run.)
    """
    path = root / LOCK_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    now = timestamp or time.strftime("%Y-%m-%dT%H:%M:%S")
    payload = json.dumps({"pid": os.getpid(), "acquired_at": now}).encode("utf-8")

    for _ in range(_MAX_ACQUIRE_ATTEMPTS):
        tmp_fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".lock.", suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "wb") as f:
                f.write(payload)

            try:
                os.link(tmp_name, path)
            except FileExistsError:
                existing_pid, acquired_at = _read_lock(path)
                if (
                    existing_pid is not None
                    and existing_pid != os.getpid()
                    and _pid_alive(existing_pid)
                ):
                    raise LockHeldError(existing_pid, acquired_at)
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
                continue

            return ForgeLock(root=root, path=path)
        finally:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass

    existing_pid, acquired_at = _read_lock(path)
    if existing_pid is not None:
        raise LockHeldError(existing_pid, acquired_at)
    raise LockHeldError(-1, "unknown")
