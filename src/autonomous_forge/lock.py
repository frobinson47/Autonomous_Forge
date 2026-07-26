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

    Acquisition itself is atomic (``O_CREAT | O_EXCL``): the check for an
    existing lock and the creation of a new one are a single OS-level
    operation, so two processes racing to acquire at the same instant can
    never both succeed — one always gets ``FileExistsError`` and re-checks
    the (now real) winner's liveness instead.
    """
    path = root / LOCK_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    now = timestamp or time.strftime("%Y-%m-%dT%H:%M:%S")
    payload = json.dumps({"pid": os.getpid(), "acquired_at": now}).encode("utf-8")

    for _ in range(_MAX_ACQUIRE_ATTEMPTS):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            existing_pid, acquired_at = _read_lock(path)
            if existing_pid is not None and existing_pid != os.getpid() and _pid_alive(existing_pid):
                raise LockHeldError(existing_pid, acquired_at)
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            continue

        with os.fdopen(fd, "wb") as f:
            f.write(payload)
        return ForgeLock(root=root, path=path)

    existing_pid, acquired_at = _read_lock(path)
    if existing_pid is not None:
        raise LockHeldError(existing_pid, acquired_at)
    raise LockHeldError(-1, "unknown")
