"""Tests for run log history."""

from __future__ import annotations

from pathlib import Path

from autonomous_forge.log import RunEntry, format_run_log, list_runs, _parse_run_file


RUN_FILE = """\
# Forge Run Summary

Timestamp: 2026-07-09T12:00:00+00:00
Task: AUTO-001 — Build widget
Policy: present and readable
Drift signals: 0
Changed files: 3

- src/foo.py
- src/bar.py
- tests/test_foo.py

Diff violations: 0

Validation: PASSED
Command: python -m pytest
"""

BLOCKED_RUN = """\
# Forge Run Summary

Timestamp: 2026-07-09T11:00:00+00:00
Task: AUTO-002 — Test widget
Policy: present and readable
Drift signals: 1
Changed files: 1

- .env

Diff violations: 1

BLOCKED: Prohibited file(s) changed: .env
"""


def _write_run(tmp_path: Path, name: str, content: str):
    runs_dir = tmp_path / ".forge" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / name).write_text(content, encoding="utf-8")


class TestParseRunFile:
    def test_parse_valid_run(self, tmp_path: Path):
        path = tmp_path / "run.md"
        path.write_text(RUN_FILE, encoding="utf-8")
        entry = _parse_run_file(path)
        assert entry is not None
        assert entry.timestamp == "2026-07-09T12:00:00+00:00"
        assert "AUTO-001" in entry.task
        assert entry.changed_files == 3
        assert entry.drift_signals == 0
        assert entry.validation == "PASSED"

    def test_parse_blocked_run(self, tmp_path: Path):
        path = tmp_path / "run.md"
        path.write_text(BLOCKED_RUN, encoding="utf-8")
        entry = _parse_run_file(path)
        assert entry is not None
        assert entry.blocked != ""
        assert "Prohibited" in entry.blocked

    def test_parse_missing_file(self, tmp_path: Path):
        entry = _parse_run_file(tmp_path / "nonexistent.md")
        assert entry is None


class TestListRuns:
    def test_no_runs_dir(self, tmp_path: Path):
        assert list_runs(tmp_path) == []

    def test_lists_runs_newest_first(self, tmp_path: Path):
        _write_run(tmp_path, "run-2026-01-01.md", RUN_FILE)
        _write_run(tmp_path, "run-2026-01-02.md", BLOCKED_RUN)
        entries = list_runs(tmp_path)
        assert len(entries) == 2
        assert "11:00" in entries[0].timestamp  # 02 file sorts after 01

    def test_limit(self, tmp_path: Path):
        _write_run(tmp_path, "run-2026-01-01.md", RUN_FILE)
        _write_run(tmp_path, "run-2026-01-02.md", BLOCKED_RUN)
        entries = list_runs(tmp_path, limit=1)
        assert len(entries) == 1


class TestFormatRunLog:
    def test_empty(self):
        text = format_run_log([])
        assert "No run history" in text

    def test_with_entries(self, tmp_path: Path):
        entry = RunEntry(
            path=tmp_path / "run.md",
            timestamp="2026-07-09T12:00:00+00:00",
            task="AUTO-001 — Build widget",
            policy="present and readable",
            drift_signals=0,
            changed_files=3,
            diff_violations=0,
            validation="PASSED",
            blocked="",
        )
        text = format_run_log([entry])
        assert "1 runs" in text
        assert "AUTO-001" in text
        assert "PASSED" in text

    def test_verbose(self, tmp_path: Path):
        entry = RunEntry(
            path=tmp_path / "run.md",
            timestamp="2026-07-09T12:00:00+00:00",
            task="AUTO-001 — Build widget",
            policy="present and readable",
            drift_signals=2,
            changed_files=3,
            diff_violations=0,
            validation="PASSED",
            blocked="",
        )
        text = format_run_log([entry], verbose=True)
        assert "Drift: 2" in text
        assert "Files: 3" in text


class TestLogCLI:
    def test_log_empty(self, tmp_path: Path, capsys):
        from autonomous_forge.cli import main

        code = main(["log", "--root", str(tmp_path)])
        captured = capsys.readouterr()
        assert code == 0
        assert "No run history" in captured.out

    def test_log_with_runs(self, tmp_path: Path, capsys):
        _write_run(tmp_path, "run-2026-01-01.md", RUN_FILE)
        from autonomous_forge.cli import main

        code = main(["log", "--root", str(tmp_path)])
        captured = capsys.readouterr()
        assert code == 0
        assert "AUTO-001" in captured.out
