"""Tests for forge plan add — adding tasks to the plan."""

from __future__ import annotations

from pathlib import Path

import pytest

from autonomous_forge.planadd import AddResult, add_task, format_add_result


PLAN = """\
# Roadmap

## Roadmap v1

### AUTO-001 — Build widget
Priority: P1
Status: DONE

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

## Future Ideas

- Hash-linked local run reports.

## Do Not Change Without Explicit Human Approval

- Remote settings.
"""


def _setup(tmp_path: Path, plan: str = PLAN) -> Path:
    ai = tmp_path / ".ai"
    ai.mkdir()
    plan_path = ai / "AUTONOMOUS_PLAN.md"
    plan_path.write_text(plan, encoding="utf-8")
    return plan_path


class TestAddTask:
    def test_add_basic_task(self, tmp_path):
        plan_path = _setup(tmp_path)
        result = add_task(
            "Ship widget",
            goal="Ship the widget to production",
            plan_path=plan_path,
        )
        assert result.added is True
        assert result.task_id == "AUTO-003"
        assert result.title == "Ship widget"
        text = plan_path.read_text(encoding="utf-8")
        assert "### AUTO-003 — Ship widget" in text
        assert "Status: TODO" in text
        assert "Goal: Ship the widget to production" in text

    def test_auto_increments_id(self, tmp_path):
        plan_path = _setup(tmp_path)
        r1 = add_task("Task A", goal="Do A", plan_path=plan_path)
        r2 = add_task("Task B", goal="Do B", plan_path=plan_path)
        assert r1.task_id == "AUTO-003"
        assert r2.task_id == "AUTO-004"

    def test_inserts_before_future_ideas(self, tmp_path):
        plan_path = _setup(tmp_path)
        add_task("Task X", goal="Do X", plan_path=plan_path)
        text = plan_path.read_text(encoding="utf-8")
        task_pos = text.index("AUTO-003")
        future_pos = text.index("## Future Ideas")
        assert task_pos < future_pos

    def test_preserves_existing_content(self, tmp_path):
        plan_path = _setup(tmp_path)
        add_task("Task Y", goal="Do Y", plan_path=plan_path)
        text = plan_path.read_text(encoding="utf-8")
        assert "AUTO-001" in text
        assert "AUTO-002" in text
        assert "## Future Ideas" in text
        assert "## Do Not Change" in text

    def test_custom_priority(self, tmp_path):
        plan_path = _setup(tmp_path)
        result = add_task("Urgent", goal="Fix now", priority="P0", plan_path=plan_path)
        assert result.added is True
        text = plan_path.read_text(encoding="utf-8")
        assert "Priority: P0" in text.split("AUTO-003")[1]

    def test_invalid_priority(self, tmp_path):
        plan_path = _setup(tmp_path)
        result = add_task("Bad", goal="Nope", priority="P9", plan_path=plan_path)
        assert result.added is False
        assert "Unsupported" in result.reason

    def test_missing_plan(self, tmp_path):
        result = add_task("Missing", goal="Gone", plan_path=tmp_path / "nope.md")
        assert result.added is False
        assert "not found" in result.reason

    def test_with_optional_fields(self, tmp_path):
        plan_path = _setup(tmp_path)
        result = add_task(
            "Detailed task",
            goal="Do something detailed",
            scope="Big scope",
            files="src/foo.py, tests/",
            acceptance="All tests pass",
            notes="Watch out for edge cases.",
            plan_path=plan_path,
        )
        assert result.added is True
        text = plan_path.read_text(encoding="utf-8")
        section = text.split("AUTO-003")[1].split("##")[0]
        assert "Scope: Big scope" in section
        assert "Expected files or areas: src/foo.py, tests/" in section
        assert "Acceptance criteria: All tests pass" in section
        assert "Notes: Watch out for edge cases." in section

    def test_plan_without_future_ideas(self, tmp_path):
        bare_plan = PLAN.split("## Future Ideas")[0]
        plan_path = _setup(tmp_path, plan=bare_plan)
        result = add_task("End task", goal="At the end", plan_path=plan_path)
        assert result.added is True
        text = plan_path.read_text(encoding="utf-8")
        assert "AUTO-003 — End task" in text


class TestFormatAddResult:
    def test_format_added(self):
        r = AddResult("AUTO-003", "Ship widget", "P1", True, "Added")
        assert "AUTO-003" in format_add_result(r)
        assert "P1/TODO" in format_add_result(r)

    def test_format_not_added(self):
        r = AddResult("", "Bad", "P9", False, "Unsupported priority: P9")
        assert "Not added" in format_add_result(r)


class TestPlanAddCLI:
    def test_add_via_cli(self, tmp_path, capsys):
        plan_path = _setup(tmp_path)
        from autonomous_forge.cli import main

        code = main([
            "plan", "add",
            "--title", "CLI task",
            "--goal", "Test CLI",
            "--plan", str(plan_path),
        ])
        captured = capsys.readouterr()
        assert code == 0
        assert "AUTO-003" in captured.out

    def test_add_with_priority_cli(self, tmp_path, capsys):
        plan_path = _setup(tmp_path)
        from autonomous_forge.cli import main

        code = main([
            "plan", "add",
            "--title", "Urgent CLI",
            "--goal", "Fix fast",
            "--priority", "P0",
            "--plan", str(plan_path),
        ])
        captured = capsys.readouterr()
        assert code == 0
        assert "P0" in captured.out

    def test_add_missing_title_exits(self, tmp_path):
        plan_path = _setup(tmp_path)
        from autonomous_forge.cli import main

        with pytest.raises(SystemExit):
            main(["plan", "add", "--goal", "No title", "--plan", str(plan_path)])
