"""Tests for forge export — JSON state export."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from autonomous_forge.export import export_state


PLAN = """\
# Roadmap

## Roadmap v1

### AUTO-001 — Build widget
Priority: P1
Status: TODO

Goal: Build a widget.
Why it matters: Yes.
Scope: Small.
Expected files or areas: src/
Acceptance criteria: Built.
Validation: Tests.
Risks or assumptions: None.
Notes: None.

### AUTO-002 — Paint widget
Priority: P2
Status: DONE

Goal: Paint it.
Why it matters: Yes.
Scope: Small.
Expected files or areas: src/
Acceptance criteria: Painted.
Validation: Tests.
Risks or assumptions: None.
Notes: None.
"""

RUN = """\
# Run Summary

Timestamp: 2026-07-09T10:00:00+00:00
Task: AUTO-001 — Build widget
Policy: present and readable
Drift signals: 0
Changed files: 3
Diff violations: 0
Validation: PASSED
"""


def _setup(tmp_path: Path, plan: str = PLAN):
    (tmp_path / ".ai").mkdir()
    (tmp_path / ".ai/AUTONOMOUS_PLAN.md").write_text(plan, encoding="utf-8")
    (tmp_path / ".forge").mkdir()
    (tmp_path / ".forge/policy.md").write_text("# Policy\n", encoding="utf-8")


class TestExportState:
    def test_basic_export(self, tmp_path):
        _setup(tmp_path)
        raw = export_state(tmp_path)
        data = json.loads(raw)
        assert data["version"] == "1"
        assert data["plan"]["found"] is True
        assert len(data["plan"]["tasks"]) == 2
        assert data["plan"]["counts"]["todo"] == 1
        assert data["plan"]["counts"]["done"] == 1
        assert data["next_task"]["id"] == "AUTO-001"
        assert data["policy"]["found"] is True

    def test_no_plan(self, tmp_path):
        raw = export_state(tmp_path)
        data = json.loads(raw)
        assert data["plan"]["found"] is False
        assert data["next_task"] is None

    def test_with_runs(self, tmp_path):
        _setup(tmp_path)
        runs = tmp_path / ".forge" / "runs"
        runs.mkdir()
        (runs / "run-2026-07-09T10-00-00.md").write_text(RUN, encoding="utf-8")
        raw = export_state(tmp_path, include_runs=True)
        data = json.loads(raw)
        assert "runs" in data
        assert len(data["runs"]) == 1
        assert data["runs"][0]["validation"] == "PASSED"

    def test_without_runs_key(self, tmp_path):
        _setup(tmp_path)
        raw = export_state(tmp_path, include_runs=False)
        data = json.loads(raw)
        assert "runs" not in data

    def test_task_structure(self, tmp_path):
        _setup(tmp_path)
        data = json.loads(export_state(tmp_path))
        task = data["plan"]["tasks"][0]
        assert task["id"] == "AUTO-001"
        assert task["title"] == "Build widget"
        assert task["priority"] == "P1"
        assert task["status"] == "TODO"


class TestTaskFilters:
    def test_filter_by_status(self, tmp_path, capsys):
        _setup(tmp_path)
        from autonomous_forge.cli import main

        code = main(["tasks", "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"), "--status", "TODO"])
        captured = capsys.readouterr()
        assert code == 0
        assert "AUTO-001" in captured.out
        assert "AUTO-002" not in captured.out

    def test_filter_by_priority(self, tmp_path, capsys):
        _setup(tmp_path)
        from autonomous_forge.cli import main

        code = main(["tasks", "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"), "--priority", "P2"])
        captured = capsys.readouterr()
        assert code == 0
        assert "AUTO-002" in captured.out
        assert "AUTO-001" not in captured.out

    def test_filter_no_match(self, tmp_path, capsys):
        _setup(tmp_path)
        from autonomous_forge.cli import main

        code = main(["tasks", "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"), "--status", "BLOCKED"])
        captured = capsys.readouterr()
        assert code == 0
        assert "No matching" in captured.out

    def test_filter_case_insensitive(self, tmp_path, capsys):
        _setup(tmp_path)
        from autonomous_forge.cli import main

        code = main(["tasks", "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"), "--status", "todo"])
        captured = capsys.readouterr()
        assert code == 0
        assert "AUTO-001" in captured.out


class TestExportCLI:
    def test_export_cli(self, tmp_path, capsys):
        _setup(tmp_path)
        from autonomous_forge.cli import main

        code = main(["export", "--root", str(tmp_path)])
        captured = capsys.readouterr()
        assert code == 0
        data = json.loads(captured.out)
        assert data["plan"]["found"] is True

    def test_export_with_runs_cli(self, tmp_path, capsys):
        _setup(tmp_path)
        from autonomous_forge.cli import main

        code = main(["export", "--root", str(tmp_path), "--runs"])
        captured = capsys.readouterr()
        assert code == 0
        data = json.loads(captured.out)
        assert "runs" in data
