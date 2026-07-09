"""Tests for forge metrics — aggregate run history stats."""

from __future__ import annotations

from pathlib import Path

import pytest

from autonomous_forge.metrics import RunMetrics, compute_metrics, format_metrics


RUN_PASSED = """\
# Run Summary

Timestamp: 2026-07-09T10:00:00+00:00
Task: AUTO-001 — Build widget
Policy: present and readable
Drift signals: 0
Changed files: 3
Diff violations: 0
Validation: PASSED
"""

RUN_FAILED = """\
# Run Summary

Timestamp: 2026-07-09T11:00:00+00:00
Task: AUTO-002 — Paint widget
Policy: present and readable
Drift signals: 1
Changed files: 2
Diff violations: 1
Validation: FAILED
"""

RUN_BLOCKED = """\
# Run Summary

Timestamp: 2026-07-09T12:00:00+00:00
Task: AUTO-001 — Build widget
Policy: present and readable
Drift signals: 0
Changed files: 1
Diff violations: 0
Validation: skipped
Blocked: Prohibited file .env detected
"""


def _setup(tmp_path: Path, runs: list[tuple[str, str]]):
    runs_dir = tmp_path / ".forge" / "runs"
    runs_dir.mkdir(parents=True)
    for name, content in runs:
        (runs_dir / name).write_text(content, encoding="utf-8")


class TestComputeMetrics:
    def test_no_runs(self, tmp_path):
        m = compute_metrics(tmp_path)
        assert m.total_runs == 0
        assert m.pass_rate == 0.0

    def test_single_pass(self, tmp_path):
        _setup(tmp_path, [("run-2026-07-09T10-00-00.md", RUN_PASSED)])
        m = compute_metrics(tmp_path)
        assert m.total_runs == 1
        assert m.passed == 1
        assert m.failed == 0
        assert m.pass_rate == 100.0

    def test_mixed_results(self, tmp_path):
        _setup(tmp_path, [
            ("run-2026-07-09T10-00-00.md", RUN_PASSED),
            ("run-2026-07-09T11-00-00.md", RUN_FAILED),
            ("run-2026-07-09T12-00-00.md", RUN_BLOCKED),
        ])
        m = compute_metrics(tmp_path)
        assert m.total_runs == 3
        assert m.passed == 1
        assert m.failed == 1
        assert m.blocked == 1
        assert m.pass_rate == 50.0
        assert m.unique_tasks == 2
        assert m.total_files_changed == 6
        assert m.total_violations == 1
        assert m.total_drift_signals == 1


class TestFormatMetrics:
    def test_format_empty(self):
        m = RunMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0)
        assert "No run history" in format_metrics(m)

    def test_format_with_data(self):
        m = RunMetrics(10, 8, 1, 1, 0, 5, 30, 2, 3, 88.9)
        text = format_metrics(m)
        assert "Total runs: 10" in text
        assert "Pass rate: 88.9%" in text
        assert "Unique tasks: 5" in text


class TestMetricsCLI:
    def test_metrics_cli_no_runs(self, tmp_path, capsys):
        from autonomous_forge.cli import main

        code = main(["metrics", "--root", str(tmp_path)])
        captured = capsys.readouterr()
        assert code == 0
        assert "No run history" in captured.out

    def test_metrics_cli_with_runs(self, tmp_path, capsys):
        _setup(tmp_path, [("run-2026-07-09T10-00-00.md", RUN_PASSED)])
        from autonomous_forge.cli import main

        code = main(["metrics", "--root", str(tmp_path)])
        captured = capsys.readouterr()
        assert code == 0
        assert "Total runs: 1" in captured.out
