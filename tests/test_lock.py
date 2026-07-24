"""Tests for the forge run/pipeline lock file."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from autonomous_forge.lock import ForgeLock, LockHeldError, acquire_lock


class TestAcquireLock:
    def test_acquires_when_no_lock_exists(self, tmp_path: Path):
        lock = acquire_lock(tmp_path, timestamp="2026-07-24T00:00:00")
        assert isinstance(lock, ForgeLock)
        lock_path = tmp_path / ".forge" / ".lock"
        assert lock_path.exists()
        data = json.loads(lock_path.read_text(encoding="utf-8"))
        assert data["pid"] == os.getpid()
        assert data["acquired_at"] == "2026-07-24T00:00:00"

    def test_release_removes_lock_file(self, tmp_path: Path):
        lock = acquire_lock(tmp_path, timestamp="2026-07-24T00:00:00")
        lock_path = tmp_path / ".forge" / ".lock"
        assert lock_path.exists()
        lock.release()
        assert not lock_path.exists()

    def test_release_is_idempotent(self, tmp_path: Path):
        lock = acquire_lock(tmp_path, timestamp="2026-07-24T00:00:00")
        lock.release()
        lock.release()  # should not raise

    def test_context_manager_releases_on_exit(self, tmp_path: Path):
        lock_path = tmp_path / ".forge" / ".lock"
        with acquire_lock(tmp_path, timestamp="2026-07-24T00:00:00"):
            assert lock_path.exists()
        assert not lock_path.exists()

    def test_second_acquire_raises_when_pid_alive(self, tmp_path: Path):
        lock_path = tmp_path / ".forge"
        lock_path.mkdir()
        (lock_path / ".lock").write_text(
            json.dumps({"pid": 999999, "acquired_at": "2026-07-24T00:00:00"}),
            encoding="utf-8",
        )
        with patch("autonomous_forge.lock._pid_alive", return_value=True):
            with pytest.raises(LockHeldError) as exc_info:
                acquire_lock(tmp_path, timestamp="2026-07-24T00:05:00")

        assert exc_info.value.pid == 999999
        assert exc_info.value.acquired_at == "2026-07-24T00:00:00"
        assert "already running (pid 999999" in str(exc_info.value)

    def test_stale_lock_is_cleared_and_reacquired(self, tmp_path: Path):
        lock_dir = tmp_path / ".forge"
        lock_dir.mkdir()
        (lock_dir / ".lock").write_text(
            json.dumps({"pid": 999999, "acquired_at": "2026-07-24T00:00:00"}),
            encoding="utf-8",
        )
        with patch("autonomous_forge.lock._pid_alive", return_value=False):
            lock = acquire_lock(tmp_path, timestamp="2026-07-24T00:05:00")

        data = json.loads((lock_dir / ".lock").read_text(encoding="utf-8"))
        assert data["pid"] == os.getpid()
        assert data["acquired_at"] == "2026-07-24T00:05:00"

    def test_malformed_lock_file_is_treated_as_stale(self, tmp_path: Path):
        lock_dir = tmp_path / ".forge"
        lock_dir.mkdir()
        (lock_dir / ".lock").write_text("not json at all {{{", encoding="utf-8")

        lock = acquire_lock(tmp_path, timestamp="2026-07-24T00:05:00")
        data = json.loads((lock_dir / ".lock").read_text(encoding="utf-8"))
        assert data["pid"] == os.getpid()

    def test_lock_holding_own_pid_does_not_self_block(self, tmp_path: Path):
        # A leftover lock from this same process (e.g. a prior acquire in
        # the same test/run that wasn't released) must not deadlock itself.
        lock_dir = tmp_path / ".forge"
        lock_dir.mkdir()
        (lock_dir / ".lock").write_text(
            json.dumps({"pid": os.getpid(), "acquired_at": "2026-07-24T00:00:00"}),
            encoding="utf-8",
        )
        lock = acquire_lock(tmp_path, timestamp="2026-07-24T00:05:00")
        assert isinstance(lock, ForgeLock)


class TestPidAlive:
    def test_current_process_is_alive(self):
        from autonomous_forge.lock import _pid_alive

        assert _pid_alive(os.getpid()) is True

    def test_implausible_pid_is_not_alive(self):
        from autonomous_forge.lock import _pid_alive

        # A PID this large should never correspond to a real process on
        # any platform this test runs on.
        assert _pid_alive(2**31 - 1) is False
