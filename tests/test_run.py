"""Tests for the autonomous run cycle."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from autonomous_forge.run import (
    RunOutcome,
    execute_run,
    format_run_outcome,
    save_run_outcome,
)


MINIMAL_PLAN = """\
# Roadmap

### AUTO-001 — Do something
Priority: P1
Status: TODO

Goal: Test task.
"""

DONE_PLAN = """\
# Roadmap

### AUTO-001 — Do something
Priority: P1
Status: DONE

Goal: Test task.
"""

MINIMAL_POLICY = """\
# Repository Policy

## Allowed paths

- `src/**`
- `tests/**`

## Prohibited paths

- `.env`
- `secrets/**`

## Human approval required

- Changing pyproject.toml.

## Validation expectations

- Run `python -m pytest` to verify.
"""


def _setup_metadata(tmp_path: Path, plan_text: str, policy_text: str | None = None):
    ai_dir = tmp_path / ".ai"
    ai_dir.mkdir()
    (ai_dir / "AUTONOMOUS_PLAN.md").write_text(plan_text, encoding="utf-8")
    (ai_dir / "AUTONOMOUS_STATE.md").write_text("- Current task: none\n", encoding="utf-8")
    (ai_dir / "AUTONOMOUS_CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    forge_dir = tmp_path / ".forge"
    forge_dir.mkdir()
    if policy_text:
        (forge_dir / "policy.md").write_text(policy_text, encoding="utf-8")


class TestExecuteRun:
    def test_no_todo_tasks(self, tmp_path: Path):
        _setup_metadata(tmp_path, DONE_PLAN, MINIMAL_POLICY)
        outcome = execute_run(
            root=tmp_path,
            timestamp="2026-01-01T00:00:00+00:00",
            dry_run=True,
        )
        assert outcome.selected_task is None
        assert outcome.block_reason == "No eligible TODO task."
        assert not outcome.blocked

    @patch("autonomous_forge.run.get_changed_files", return_value=[])
    def test_selects_task_dry_run(self, mock_git, tmp_path: Path):
        _setup_metadata(tmp_path, MINIMAL_PLAN, MINIMAL_POLICY)
        outcome = execute_run(
            root=tmp_path,
            timestamp="2026-01-01T00:00:00+00:00",
            dry_run=True,
        )
        assert outcome.selected_task is not None
        assert outcome.selected_task.task_id == "AUTO-001"
        assert outcome.validation_command == "skipped (dry run)"
        assert not outcome.blocked

    @patch("autonomous_forge.run.get_changed_files", return_value=[".env"])
    def test_blocked_by_prohibited_file(self, mock_git, tmp_path: Path):
        _setup_metadata(tmp_path, MINIMAL_PLAN, MINIMAL_POLICY)
        outcome = execute_run(
            root=tmp_path,
            timestamp="2026-01-01T00:00:00+00:00",
            dry_run=True,
        )
        assert outcome.blocked
        assert ".env" in outcome.block_reason

    @patch("autonomous_forge.run.get_changed_files", return_value=["src/foo.py"])
    def test_no_violations_dry_run(self, mock_git, tmp_path: Path):
        _setup_metadata(tmp_path, MINIMAL_PLAN, MINIMAL_POLICY)
        outcome = execute_run(
            root=tmp_path,
            timestamp="2026-01-01T00:00:00+00:00",
            dry_run=True,
        )
        assert not outcome.blocked
        assert outcome.diff_violations == 0
        assert "src/foo.py" in outcome.changed_files

    @patch("autonomous_forge.run.get_changed_files", return_value=[])
    def test_no_validate_flag(self, mock_git, tmp_path: Path):
        _setup_metadata(tmp_path, MINIMAL_PLAN, MINIMAL_POLICY)
        outcome = execute_run(
            root=tmp_path,
            timestamp="2026-01-01T00:00:00+00:00",
            validate=False,
        )
        assert outcome.validation_passed is None
        assert outcome.validation_command == ""

    def test_no_policy_file(self, tmp_path: Path):
        _setup_metadata(tmp_path, DONE_PLAN)
        outcome = execute_run(
            root=tmp_path,
            timestamp="2026-01-01T00:00:00+00:00",
            dry_run=True,
        )
        assert outcome.policy_status == "not found"

    @patch("autonomous_forge.run.get_changed_files", return_value=[])
    def test_policy_present(self, mock_git, tmp_path: Path):
        _setup_metadata(tmp_path, MINIMAL_PLAN, MINIMAL_POLICY)
        outcome = execute_run(
            root=tmp_path,
            timestamp="2026-01-01T00:00:00+00:00",
            dry_run=True,
        )
        assert outcome.policy_status == "present and readable"


class TestFormatRunOutcome:
    def test_idle_format(self):
        outcome = RunOutcome(
            timestamp="2026-01-01T00:00:00+00:00",
            selected_task=None,
            validation_passed=None,
            validation_command="",
            validation_output="",
            diff_violations=0,
            diff_details=(),
            drift_signals=0,
            changed_files=(),
            policy_status="present and readable",
            blocked=False,
            block_reason="No eligible TODO task.",
        )
        text = format_run_outcome(outcome)
        assert "idle" in text
        assert "Selected task: none" in text

    def test_blocked_format(self):
        outcome = RunOutcome(
            timestamp="2026-01-01T00:00:00+00:00",
            selected_task=None,
            validation_passed=None,
            validation_command="",
            validation_output="",
            diff_violations=1,
            diff_details=("[prohibited] .env: prohibited file",),
            drift_signals=0,
            changed_files=(".env",),
            policy_status="present and readable",
            blocked=True,
            block_reason="Prohibited file(s) changed: .env",
        )
        text = format_run_outcome(outcome)
        assert "BLOCKED" in text

    def test_ready_to_commit(self):
        from autonomous_forge.plan import PlanTask

        task = PlanTask(
            task_id="AUTO-001",
            title="Test",
            priority="P1",
            status="TODO",
            line_number=1,
        )
        outcome = RunOutcome(
            timestamp="2026-01-01T00:00:00+00:00",
            selected_task=task,
            validation_passed=True,
            validation_command="python -m pytest",
            validation_output="all passed",
            diff_violations=0,
            diff_details=(),
            drift_signals=0,
            changed_files=("src/foo.py",),
            policy_status="present and readable",
            blocked=False,
            block_reason="",
        )
        text = format_run_outcome(outcome)
        assert "ready to commit" in text
        assert "AUTO-001" in text


class TestSaveRunOutcome:
    def test_saves_to_disk(self, tmp_path: Path):
        outcome = RunOutcome(
            timestamp="2026-01-01T00:00:00+00:00",
            selected_task=None,
            validation_passed=None,
            validation_command="",
            validation_output="",
            diff_violations=0,
            diff_details=(),
            drift_signals=0,
            changed_files=(),
            policy_status="not found",
            blocked=False,
            block_reason="No eligible TODO task.",
        )
        path = save_run_outcome(outcome, tmp_path)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Forge Run Summary" in content
        assert "Task: none" in content

    def test_creates_runs_directory(self, tmp_path: Path):
        outcome = RunOutcome(
            timestamp="2026-01-01T00:00:00+00:00",
            selected_task=None,
            validation_passed=None,
            validation_command="",
            validation_output="",
            diff_violations=0,
            diff_details=(),
            drift_signals=0,
            changed_files=(),
            policy_status="not found",
            blocked=False,
            block_reason="No eligible TODO task.",
        )
        save_run_outcome(outcome, tmp_path)
        assert (tmp_path / ".forge" / "runs").is_dir()


class TestRunCLI:
    def test_run_dry_run(self, tmp_path: Path, capsys):
        _setup_metadata(tmp_path, MINIMAL_PLAN, MINIMAL_POLICY)
        from autonomous_forge.cli import main

        with patch("autonomous_forge.run.get_changed_files", return_value=[]):
            code = main([
                "run",
                "--root", str(tmp_path),
                "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"),
                "--policy", str(tmp_path / ".forge/policy.md"),
                "--dry-run",
                "--timestamp", "2026-01-01T00:00:00+00:00",
            ])
        captured = capsys.readouterr()
        assert code == 0
        assert "AUTO-001" in captured.out
        assert "dry run" in captured.out

    def test_run_no_save(self, tmp_path: Path, capsys):
        _setup_metadata(tmp_path, DONE_PLAN, MINIMAL_POLICY)
        from autonomous_forge.cli import main

        code = main([
            "run",
            "--root", str(tmp_path),
            "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"),
            "--policy", str(tmp_path / ".forge/policy.md"),
            "--dry-run",
            "--no-save",
            "--timestamp", "2026-01-01T00:00:00+00:00",
        ])
        captured = capsys.readouterr()
        assert code == 0
        assert "Run saved" not in captured.out

    def test_run_blocked_returns_1(self, tmp_path: Path, capsys):
        _setup_metadata(tmp_path, MINIMAL_PLAN, MINIMAL_POLICY)
        from autonomous_forge.cli import main

        with patch("autonomous_forge.run.get_changed_files", return_value=[".env"]):
            code = main([
                "run",
                "--root", str(tmp_path),
                "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"),
                "--policy", str(tmp_path / ".forge/policy.md"),
                "--dry-run",
                "--no-save",
                "--timestamp", "2026-01-01T00:00:00+00:00",
            ])
        assert code == 1
        captured = capsys.readouterr()
        assert "BLOCKED" in captured.out
