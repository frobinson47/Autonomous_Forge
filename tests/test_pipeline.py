"""Tests for the full autonomous pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from autonomous_forge.commit import CommitPreFlight, CommitResult
from autonomous_forge.pipeline import (
    PipelineResult,
    execute_pipeline,
    format_pipeline_result,
)
from autonomous_forge.push import PushResult


PLAN_TODO = """\
# Roadmap

## Roadmap v1

### AUTO-001 — Build widget
Priority: P1
Status: TODO

Goal: Build a widget.
"""

PLAN_DONE = """\
# Roadmap

## Roadmap v1

### AUTO-001 — Build widget
Priority: P1
Status: DONE

Goal: Build a widget.
"""

POLICY = """\
# Repository Policy

## Allowed paths

- `src/**`
- `tests/**`

## Prohibited paths

- `.env`

## Human approval required

- Changing production config.

## Validation expectations

- Run `python -c "exit(0)"` to verify.
"""


def _setup(tmp_path: Path, plan: str = PLAN_TODO):
    (tmp_path / ".ai").mkdir()
    (tmp_path / ".ai/AUTONOMOUS_PLAN.md").write_text(plan, encoding="utf-8")
    (tmp_path / ".ai/AUTONOMOUS_STATE.md").write_text("- Current task: none\n", encoding="utf-8")
    (tmp_path / ".ai/AUTONOMOUS_CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    (tmp_path / ".forge").mkdir()
    (tmp_path / ".forge/policy.md").write_text(POLICY, encoding="utf-8")


class TestExecutePipeline:
    @patch("autonomous_forge.run.get_changed_files", return_value=[])
    def test_dry_run_no_commit(self, mock_git, tmp_path):
        _setup(tmp_path)
        result = execute_pipeline(
            root=tmp_path,
            dry_run=True,
            timestamp="2026-01-01T00:00:00+00:00",
        )
        assert result.stage_reached == "run"
        assert "Commit not requested" in result.stopped_reason
        assert result.commit_result is None

    def test_blocked_when_lock_already_held(self, tmp_path):
        import json

        _setup(tmp_path)
        (tmp_path / ".forge/.lock").write_text(
            json.dumps({"pid": 999999, "acquired_at": "2026-01-01T00:00:00"}),
            encoding="utf-8",
        )
        with patch("autonomous_forge.lock._pid_alive", return_value=True):
            result = execute_pipeline(
                root=tmp_path,
                dry_run=True,
                timestamp="2026-01-01T00:05:00+00:00",
            )
        assert result.stage_reached == "run"
        assert "already running (pid 999999" in result.stopped_reason
        assert result.run_outcome.blocked

    def test_releases_lock_after_pipeline(self, tmp_path):
        _setup(tmp_path, plan=PLAN_DONE)
        execute_pipeline(root=tmp_path, dry_run=True, timestamp="2026-01-01T00:00:00+00:00")
        assert not (tmp_path / ".forge" / ".lock").exists()

    @patch("autonomous_forge.run.get_changed_files", return_value=[".env"])
    def test_blocked_by_prohibited(self, mock_git, tmp_path):
        _setup(tmp_path)
        result = execute_pipeline(
            root=tmp_path,
            dry_run=True,
            timestamp="2026-01-01T00:00:00+00:00",
        )
        assert result.stage_reached == "run"
        assert "Blocked" in result.stopped_reason

    @patch("autonomous_forge.run.get_changed_files", return_value=[])
    def test_no_todo_tasks(self, mock_git, tmp_path):
        _setup(tmp_path, plan=PLAN_DONE)
        result = execute_pipeline(
            root=tmp_path,
            dry_run=True,
            timestamp="2026-01-01T00:00:00+00:00",
        )
        assert result.stage_reached == "run"
        assert "nothing to do" in result.stopped_reason

    def _fake_commit_result(self) -> CommitResult:
        pf = CommitPreFlight(
            safe=True, changed_files=("src/foo.py",), violations=(),
            validation_passed=True, validation_output="",
            task_id="AUTO-001", task_title="Build widget", block_reason="",
        )
        return CommitResult(
            committed=True, commit_hash="abc1234",
            message="forge: AUTO-001 — Build widget", pre_flight=pf,
        )

    @patch("autonomous_forge.run.get_changed_files", return_value=[])
    @patch("autonomous_forge.pipeline.execute_commit")
    def test_commit_without_push_stops_at_commit(self, mock_commit, mock_git, tmp_path):
        _setup(tmp_path)
        mock_commit.return_value = self._fake_commit_result()
        result = execute_pipeline(
            root=tmp_path,
            commit=True,
            dry_run=True,
            timestamp="2026-01-01T00:00:00+00:00",
        )
        assert result.stage_reached == "commit"
        assert "Push not requested" in result.stopped_reason
        assert result.push_result is None

    @patch("autonomous_forge.run.get_changed_files", return_value=[])
    @patch("autonomous_forge.pipeline.execute_commit")
    def test_commit_records_hash_on_run_report(self, mock_commit, mock_git, tmp_path):
        _setup(tmp_path)
        mock_commit.return_value = self._fake_commit_result()
        result = execute_pipeline(
            root=tmp_path,
            commit=True,
            dry_run=True,
            timestamp="2026-01-01T00:00:00+00:00",
        )
        run_files = list((tmp_path / ".forge" / "runs").glob("run-*.md"))
        assert len(run_files) == 1
        content = run_files[0].read_text(encoding="utf-8")
        assert "Commit: abc1234" in content

    @patch("autonomous_forge.run.get_changed_files", return_value=[])
    @patch("autonomous_forge.pipeline.execute_push")
    @patch("autonomous_forge.pipeline.execute_commit")
    def test_push_without_sync_stops_at_push(self, mock_commit, mock_push, mock_git, tmp_path):
        _setup(tmp_path)
        mock_commit.return_value = self._fake_commit_result()
        mock_push.return_value = PushResult(
            pushed=True, remote="origin", branch="main",
            commits_pushed=1, message="Pushed 1 commit(s) to origin/main.",
        )
        result = execute_pipeline(
            root=tmp_path,
            commit=True,
            push=True,
            dry_run=True,
            timestamp="2026-01-01T00:00:00+00:00",
        )
        assert result.stage_reached == "push"
        assert "Sync not requested" in result.stopped_reason
        assert result.push_result.pushed

    @patch("autonomous_forge.run.get_changed_files", return_value=[])
    @patch("autonomous_forge.pipeline.execute_sync")
    @patch("autonomous_forge.pipeline.execute_push")
    @patch("autonomous_forge.pipeline.execute_commit")
    def test_push_failure_stops_before_sync(
        self, mock_commit, mock_push, mock_sync, mock_git, tmp_path
    ):
        _setup(tmp_path)
        mock_commit.return_value = self._fake_commit_result()
        mock_push.return_value = PushResult(
            pushed=False, remote="origin", branch="main",
            commits_pushed=0, message="git push failed: rejected",
        )
        result = execute_pipeline(
            root=tmp_path,
            commit=True,
            push=True,
            sync=True,
            dry_run=True,
            timestamp="2026-01-01T00:00:00+00:00",
        )
        assert result.stage_reached == "push"
        assert "Push failed" in result.stopped_reason
        assert not mock_sync.called


class TestFormatPipelineResult:
    def test_format_run_only(self):
        from autonomous_forge.run import RunOutcome
        from autonomous_forge.plan import PlanTask

        task = PlanTask("AUTO-001", "Build widget", "P1", "TODO", 1)
        ro = RunOutcome(
            timestamp="2026-01-01T00:00:00+00:00",
            selected_task=task,
            validation_passed=None,
            validation_command="skipped",
            validation_output="",
            diff_violations=0,
            diff_details=(),
            drift_signals=0,
            changed_files=("src/foo.py",),
            policy_status="present",
            blocked=False,
            block_reason="",
        )
        result = PipelineResult(
            run_outcome=ro,
            commit_result=None,
            push_result=None,
            sync_result=None,
            stage_reached="run",
            stopped_reason="Commit not requested.",
        )
        text = format_pipeline_result(result)
        assert "AUTO-001" in text
        assert "Stopped" in text
        assert "run" in text


class TestPipelineCLI:
    @patch("autonomous_forge.run.get_changed_files", return_value=[])
    def test_pipeline_dry_run(self, mock_git, tmp_path, capsys):
        _setup(tmp_path)
        from autonomous_forge.cli import main

        code = main([
            "pipeline",
            "--root", str(tmp_path),
            "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"),
            "--policy", str(tmp_path / ".forge/policy.md"),
            "--dry-run",
            "--timestamp", "2026-01-01T00:00:00+00:00",
        ])
        captured = capsys.readouterr()
        assert code == 0
        assert "AUTO-001" in captured.out

    @patch("autonomous_forge.run.get_changed_files", return_value=[".env"])
    def test_pipeline_blocked_exits_1(self, mock_git, tmp_path, capsys):
        _setup(tmp_path)
        from autonomous_forge.cli import main

        code = main([
            "pipeline",
            "--root", str(tmp_path),
            "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"),
            "--policy", str(tmp_path / ".forge/policy.md"),
            "--dry-run",
            "--timestamp", "2026-01-01T00:00:00+00:00",
        ])
        assert code == 1
