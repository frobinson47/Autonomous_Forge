"""Tests for forge mark — task status updates."""

from __future__ import annotations

from pathlib import Path

import pytest

from autonomous_forge.mark import MarkResult, format_mark_result, mark_task_status


PLAN = """\
# Roadmap

## Roadmap v1

### AUTO-001 — Build widget
Priority: P1
Status: TODO

Goal: Build a widget.
Why it matters: Widgets matter.
Scope: Small.
Expected files or areas: src/
Acceptance criteria: Widget exists.
Validation: Tests pass.
Risks or assumptions: None.
Notes: None.

### AUTO-002 — Paint widget
Priority: P2
Status: DONE

Goal: Paint it.
Why it matters: Looks good.
Scope: Small.
Expected files or areas: src/
Acceptance criteria: Paint applied.
Validation: Tests pass.
Risks or assumptions: None.
Notes: None.

### AUTO-003 — Ship widget
Priority: P1
Status: BLOCKED

Goal: Ship it.
Why it matters: Users need it.
Scope: Small.
Expected files or areas: src/
Acceptance criteria: Shipped.
Validation: Tests pass.
Risks or assumptions: None.
Notes: None.
"""


def _setup(tmp_path: Path, plan: str = PLAN) -> Path:
    ai = tmp_path / ".ai"
    ai.mkdir()
    plan_path = ai / "AUTONOMOUS_PLAN.md"
    plan_path.write_text(plan, encoding="utf-8")
    return plan_path


class TestMarkTaskStatus:
    def test_mark_todo_to_done(self, tmp_path):
        plan_path = _setup(tmp_path)
        result = mark_task_status("AUTO-001", "DONE", plan_path)
        assert result.updated is True
        assert result.old_status == "TODO"
        assert result.new_status == "DONE"
        text = plan_path.read_text(encoding="utf-8")
        assert "Status: DONE" in text.split("AUTO-001")[1].split("AUTO-002")[0]

    def test_mark_done_to_todo(self, tmp_path):
        plan_path = _setup(tmp_path)
        result = mark_task_status("AUTO-002", "TODO", plan_path)
        assert result.updated is True
        assert result.old_status == "DONE"

    def test_mark_blocked_to_done(self, tmp_path):
        plan_path = _setup(tmp_path)
        result = mark_task_status("AUTO-003", "DONE", plan_path)
        assert result.updated is True
        assert result.old_status == "BLOCKED"

    def test_mark_same_status_noop(self, tmp_path):
        plan_path = _setup(tmp_path)
        result = mark_task_status("AUTO-001", "TODO", plan_path)
        assert result.updated is False
        assert "Already" in result.reason

    def test_mark_nonexistent_task(self, tmp_path):
        plan_path = _setup(tmp_path)
        result = mark_task_status("AUTO-999", "DONE", plan_path)
        assert result.updated is False
        assert "not found" in result.reason

    def test_mark_unsupported_status(self, tmp_path):
        plan_path = _setup(tmp_path)
        result = mark_task_status("AUTO-001", "INVALID", plan_path)
        assert result.updated is False
        assert "Unsupported" in result.reason

    def test_mark_missing_plan(self, tmp_path):
        result = mark_task_status("AUTO-001", "DONE", tmp_path / "nope.md")
        assert result.updated is False
        assert "not found" in result.reason

    def test_mark_preserves_other_tasks(self, tmp_path):
        plan_path = _setup(tmp_path)
        mark_task_status("AUTO-001", "DONE", plan_path)
        text = plan_path.read_text(encoding="utf-8")
        assert "AUTO-002" in text
        assert "AUTO-003" in text
        # AUTO-002 should still be DONE
        section_002 = text.split("AUTO-002")[1].split("AUTO-003")[0]
        assert "Status: DONE" in section_002

    def test_mark_multiple_sequential(self, tmp_path):
        plan_path = _setup(tmp_path)
        mark_task_status("AUTO-001", "DONE", plan_path)
        mark_task_status("AUTO-003", "TODO", plan_path)
        text = plan_path.read_text(encoding="utf-8")
        section_001 = text.split("AUTO-001")[1].split("AUTO-002")[0]
        section_003 = text.split("AUTO-003")[1]
        assert "Status: DONE" in section_001
        assert "Status: TODO" in section_003


class TestFormatMarkResult:
    def test_format_updated(self):
        r = MarkResult("AUTO-001", "TODO", "DONE", True, "TODO -> DONE")
        assert "AUTO-001" in format_mark_result(r)
        assert "TODO -> DONE" in format_mark_result(r)

    def test_format_not_updated(self):
        r = MarkResult("AUTO-001", "TODO", "TODO", False, "Already TODO")
        assert "Already" in format_mark_result(r)


class TestMarkCLI:
    def test_mark_via_cli(self, tmp_path, capsys):
        plan_path = _setup(tmp_path)
        from autonomous_forge.cli import main

        code = main(["mark", "AUTO-001", "DONE", "--plan", str(plan_path)])
        captured = capsys.readouterr()
        assert code == 0
        assert "DONE" in captured.out

    def test_mark_invalid_status_cli(self, tmp_path, capsys):
        plan_path = _setup(tmp_path)
        from autonomous_forge.cli import main

        code = main(["mark", "AUTO-001", "NOPE", "--plan", str(plan_path)])
        assert code == 1

    def test_mark_nonexistent_task_cli(self, tmp_path, capsys):
        plan_path = _setup(tmp_path)
        from autonomous_forge.cli import main

        code = main(["mark", "AUTO-999", "DONE", "--plan", str(plan_path)])
        assert code == 1
