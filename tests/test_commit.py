"""Tests for the safe auto-commit module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from autonomous_forge.commit import (
    CommitPreFlight,
    CommitResult,
    execute_commit,
    format_commit_result,
    format_pre_flight,
    run_pre_flight,
)


PLAN_WITH_TODO = """\
# Roadmap

### AUTO-001 — Build widget
Priority: P1
Status: TODO

Goal: Build a widget.
"""

PLAN_ALL_DONE = """\
# Roadmap

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


def _setup(tmp_path: Path, plan: str = PLAN_WITH_TODO, policy: str = POLICY):
    (tmp_path / ".ai").mkdir()
    (tmp_path / ".ai/AUTONOMOUS_PLAN.md").write_text(plan, encoding="utf-8")
    (tmp_path / ".forge").mkdir()
    (tmp_path / ".forge/policy.md").write_text(policy, encoding="utf-8")


class TestPreFlight:
    @patch("autonomous_forge.commit.get_changed_files", return_value=[])
    def test_no_changes(self, mock_git, tmp_path):
        _setup(tmp_path)
        pf = run_pre_flight(root=tmp_path, validate=False)
        assert not pf.safe
        assert "No changed files" in pf.block_reason

    @patch("autonomous_forge.commit.get_changed_files", return_value=["src/foo.py"])
    def test_clean_changes(self, mock_git, tmp_path):
        _setup(tmp_path)
        pf = run_pre_flight(root=tmp_path, validate=False)
        assert pf.safe
        assert pf.task_id == "AUTO-001"
        assert "src/foo.py" in pf.changed_files

    @patch("autonomous_forge.commit.get_changed_files", return_value=[".env"])
    def test_prohibited_blocks(self, mock_git, tmp_path):
        _setup(tmp_path)
        pf = run_pre_flight(root=tmp_path, validate=False)
        assert not pf.safe
        assert ".env" in pf.block_reason

    @patch("autonomous_forge.commit.get_changed_files", return_value=["src/foo.py"])
    @patch("autonomous_forge.commit.run_validation")
    def test_validation_failure_blocks(self, mock_val, mock_git, tmp_path):
        _setup(tmp_path)
        mock_val.return_value = MagicMock(
            passed=False, command="pytest", stdout="FAIL", stderr=""
        )
        pf = run_pre_flight(root=tmp_path, validate=True)
        assert not pf.safe
        assert "Validation failed" in pf.block_reason

    @patch("autonomous_forge.commit.get_changed_files", return_value=["src/foo.py"])
    def test_no_plan_still_works(self, mock_git, tmp_path):
        (tmp_path / ".forge").mkdir()
        (tmp_path / ".forge/policy.md").write_text(POLICY, encoding="utf-8")
        pf = run_pre_flight(root=tmp_path, validate=False)
        assert pf.safe
        assert pf.task_id == ""

    @patch("autonomous_forge.commit.get_changed_files", return_value=["src/foo.py"])
    def test_all_done_no_task(self, mock_git, tmp_path):
        _setup(tmp_path, plan=PLAN_ALL_DONE)
        pf = run_pre_flight(root=tmp_path, validate=False)
        assert pf.safe
        assert pf.task_id == ""


class TestExecuteCommit:
    @patch("autonomous_forge.commit.get_changed_files", return_value=[])
    def test_no_changes_no_commit(self, mock_git, tmp_path):
        _setup(tmp_path)
        result = execute_commit(root=tmp_path, validate=False)
        assert not result.committed

    def test_pre_flight_blocked_no_commit(self, tmp_path):
        pf = CommitPreFlight(
            safe=False,
            changed_files=(".env",),
            violations=("[prohibited] .env: prohibited",),
            validation_passed=None,
            validation_output="",
            task_id="AUTO-001",
            task_title="Build widget",
            block_reason="Prohibited file(s): .env",
        )
        result = execute_commit(root=tmp_path, pre_flight=pf)
        assert not result.committed
        assert "Prohibited" in result.message


class TestFormatPreFlight:
    def test_safe(self):
        pf = CommitPreFlight(
            safe=True,
            changed_files=("src/foo.py",),
            violations=(),
            validation_passed=True,
            validation_output="",
            task_id="AUTO-001",
            task_title="Build widget",
            block_reason="",
        )
        text = format_pre_flight(pf)
        assert "SAFE" in text
        assert "AUTO-001" in text

    def test_blocked(self):
        pf = CommitPreFlight(
            safe=False,
            changed_files=(".env",),
            violations=("[prohibited] .env: prohibited",),
            validation_passed=None,
            validation_output="",
            task_id="",
            task_title="",
            block_reason="Prohibited file(s): .env",
        )
        text = format_pre_flight(pf)
        assert "BLOCKED" in text


class TestFormatCommitResult:
    def test_committed(self):
        pf = CommitPreFlight(
            safe=True, changed_files=("src/foo.py",), violations=(),
            validation_passed=True, validation_output="",
            task_id="AUTO-001", task_title="Build widget", block_reason="",
        )
        result = CommitResult(
            committed=True, commit_hash="abc1234",
            message="forge: AUTO-001 — Build widget", pre_flight=pf,
        )
        text = format_commit_result(result)
        assert "Committed: abc1234" in text

    def test_not_committed(self):
        pf = CommitPreFlight(
            safe=False, changed_files=(), violations=(),
            validation_passed=None, validation_output="",
            task_id="", task_title="", block_reason="No changed files to commit.",
        )
        result = CommitResult(
            committed=False, commit_hash="", message="No changed files to commit.",
            pre_flight=pf,
        )
        text = format_commit_result(result)
        assert "Not committed" in text


class TestCommitCLI:
    @patch("autonomous_forge.commit.get_changed_files", return_value=["src/foo.py"])
    def test_check_only(self, mock_git, tmp_path, capsys):
        _setup(tmp_path)
        from autonomous_forge.cli import main

        code = main([
            "commit", "--check-only", "--no-validate",
            "--root", str(tmp_path),
            "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"),
            "--policy", str(tmp_path / ".forge/policy.md"),
        ])
        captured = capsys.readouterr()
        assert code == 0
        assert "SAFE" in captured.out

    @patch("autonomous_forge.commit.get_changed_files", return_value=[".env"])
    def test_check_only_blocked(self, mock_git, tmp_path, capsys):
        _setup(tmp_path)
        from autonomous_forge.cli import main

        code = main([
            "commit", "--check-only", "--no-validate",
            "--root", str(tmp_path),
            "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"),
            "--policy", str(tmp_path / ".forge/policy.md"),
        ])
        captured = capsys.readouterr()
        assert code == 1
        assert "BLOCKED" in captured.out
