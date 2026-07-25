"""Tests for forge revert — undo a completed task's commit."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from autonomous_forge.revert import (
    RevertResult,
    _find_commit_for_task,
    execute_revert,
    format_revert_result,
)


PLAN_DONE = """\
# Roadmap

### AUTO-001 — Build widget
Priority: P1
Status: DONE

Goal: Build a widget.
"""


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=30,
    )


def _init_real_repo(tmp_path: Path) -> None:
    _git(["init"], tmp_path)
    _git(["config", "user.email", "test@example.com"], tmp_path)
    _git(["config", "user.name", "Test"], tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.py").write_text("original\n", encoding="utf-8")
    result = _git(["add", "-A"], tmp_path)
    assert result.returncode == 0
    result = _git(["commit", "-m", "initial"], tmp_path)
    assert result.returncode == 0


def _write_run_with_commit(tmp_path: Path, task: str, commit_hash: str, timestamp: str) -> None:
    runs_dir = tmp_path / ".forge" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    safe_ts = timestamp.replace(":", "-")
    (runs_dir / f"run-{safe_ts}.md").write_text(
        f"# Forge Run Summary\n\nTimestamp: {timestamp}\nTask: {task}\nCommit: {commit_hash}\n",
        encoding="utf-8",
    )


class TestFindCommitForTask:
    def test_finds_matching_commit(self, tmp_path: Path):
        _write_run_with_commit(tmp_path, "AUTO-001 — Build widget", "abc1234", "2026-07-25T10-00-00")
        commit = _find_commit_for_task("AUTO-001", tmp_path)
        assert commit == "abc1234"

    def test_returns_none_when_no_match(self, tmp_path: Path):
        _write_run_with_commit(tmp_path, "AUTO-002 — Other task", "abc1234", "2026-07-25T10-00-00")
        commit = _find_commit_for_task("AUTO-001", tmp_path)
        assert commit is None

    def test_returns_none_when_no_commit_recorded(self, tmp_path: Path):
        runs_dir = tmp_path / ".forge" / "runs"
        runs_dir.mkdir(parents=True)
        (runs_dir / "run-2026-07-25T10-00-00.md").write_text(
            "# Forge Run Summary\n\nTimestamp: 2026-07-25T10:00:00\nTask: AUTO-001 — Build widget\n",
            encoding="utf-8",
        )
        commit = _find_commit_for_task("AUTO-001", tmp_path)
        assert commit is None

    def test_picks_most_recent_match(self, tmp_path: Path):
        _write_run_with_commit(tmp_path, "AUTO-001 — Build widget", "older111", "2026-07-25T09-00-00")
        _write_run_with_commit(tmp_path, "AUTO-001 — Build widget", "newer222", "2026-07-25T10-00-00")
        commit = _find_commit_for_task("AUTO-001", tmp_path)
        assert commit == "newer222"


class TestExecuteRevert:
    def test_no_commit_found_fails_cleanly(self, tmp_path: Path):
        (tmp_path / ".ai").mkdir()
        (tmp_path / ".ai" / "AUTONOMOUS_PLAN.md").write_text(PLAN_DONE, encoding="utf-8")

        result = execute_revert("AUTO-001", root=tmp_path)

        assert not result.reverted
        assert "No recorded commit" in result.message

    def test_reverts_commit_and_flips_status_to_todo(self, tmp_path: Path):
        _init_real_repo(tmp_path)
        (tmp_path / ".ai").mkdir()
        (tmp_path / ".ai" / "AUTONOMOUS_PLAN.md").write_text(PLAN_DONE, encoding="utf-8")
        _git(["add", "-A"], tmp_path)
        _git(["commit", "-m", "add plan"], tmp_path)

        # The commit under test: change src/foo.py.
        (tmp_path / "src" / "foo.py").write_text("changed by AUTO-001\n", encoding="utf-8")
        _git(["add", "-A"], tmp_path)
        _git(["commit", "-m", "forge: AUTO-001 — Build widget"], tmp_path)
        target_hash = _git(["rev-parse", "--short", "HEAD"], tmp_path).stdout.strip()

        _write_run_with_commit(tmp_path, "AUTO-001 — Build widget", target_hash, "2026-07-25T10-00-00")

        result = execute_revert("AUTO-001", root=tmp_path)

        assert result.reverted
        assert result.original_commit == target_hash
        assert result.revert_commit_hash
        assert result.status_updated

        content = (tmp_path / "src" / "foo.py").read_text(encoding="utf-8")
        assert content == "original\n"  # the revert undid the change

        plan_text = (tmp_path / ".ai" / "AUTONOMOUS_PLAN.md").read_text(encoding="utf-8")
        assert "Status: TODO" in plan_text

        # revert commit exists on top of HEAD
        log = _git(["log", "--oneline", "-1"], tmp_path).stdout
        assert result.revert_commit_hash in log

    def test_commit_override_takes_precedence_over_run_history(self, tmp_path: Path):
        _init_real_repo(tmp_path)
        (tmp_path / ".ai").mkdir()
        (tmp_path / ".ai" / "AUTONOMOUS_PLAN.md").write_text(PLAN_DONE, encoding="utf-8")
        _git(["add", "-A"], tmp_path)
        _git(["commit", "-m", "add plan"], tmp_path)

        (tmp_path / "src" / "foo.py").write_text("changed\n", encoding="utf-8")
        _git(["add", "-A"], tmp_path)
        _git(["commit", "-m", "the target commit"], tmp_path)
        target_hash = _git(["rev-parse", "--short", "HEAD"], tmp_path).stdout.strip()

        # Deliberately wrong recorded commit — override should win.
        _write_run_with_commit(tmp_path, "AUTO-001 — Build widget", "0000000", "2026-07-25T10-00-00")

        result = execute_revert("AUTO-001", root=tmp_path, commit_override=target_hash)

        assert result.reverted
        assert result.original_commit == target_hash

    def test_conflicting_revert_fails_and_leaves_clean_tree(self, tmp_path: Path):
        _init_real_repo(tmp_path)
        (tmp_path / ".ai").mkdir()
        (tmp_path / ".ai" / "AUTONOMOUS_PLAN.md").write_text(PLAN_DONE, encoding="utf-8")
        _git(["add", "-A"], tmp_path)
        _git(["commit", "-m", "add plan"], tmp_path)

        # Commit to revert: first change.
        (tmp_path / "src" / "foo.py").write_text("first change\n", encoding="utf-8")
        _git(["add", "-A"], tmp_path)
        _git(["commit", "-m", "first change"], tmp_path)
        target_hash = _git(["rev-parse", "--short", "HEAD"], tmp_path).stdout.strip()

        # A later, conflicting change to the same lines.
        (tmp_path / "src" / "foo.py").write_text("second, conflicting change\n", encoding="utf-8")
        _git(["add", "-A"], tmp_path)
        _git(["commit", "-m", "second change"], tmp_path)

        _write_run_with_commit(tmp_path, "AUTO-001 — Build widget", target_hash, "2026-07-25T10-00-00")

        result = execute_revert("AUTO-001", root=tmp_path)

        assert not result.reverted
        assert "git revert failed" in result.message

        # No half-finished revert left behind (the .forge/ run-history dir
        # itself is expectedly untracked — that's test setup, not revert state).
        assert not (tmp_path / ".git" / "REVERT_HEAD").exists()
        tracked_status = _git(["status", "--porcelain", "--", "src", ".ai"], tmp_path).stdout
        assert tracked_status.strip() == ""

        # Plan status must be untouched since the revert never completed.
        plan_text = (tmp_path / ".ai" / "AUTONOMOUS_PLAN.md").read_text(encoding="utf-8")
        assert "Status: DONE" in plan_text


class TestFormatRevertResult:
    def test_reverted(self):
        result = RevertResult(
            task_id="AUTO-001", reverted=True, original_commit="abc1234",
            revert_commit_hash="def5678", status_updated=True,
            message="Reverted abc1234 as def5678. Status: DONE -> TODO.",
        )
        text = format_revert_result(result)
        assert "REVERTED" in text
        assert "abc1234" in text

    def test_failed(self):
        result = RevertResult(
            task_id="AUTO-001", reverted=False, original_commit="", revert_commit_hash="",
            status_updated=False, message="No recorded commit found for AUTO-001.",
        )
        text = format_revert_result(result)
        assert "FAILED" in text


class TestRevertCLI:
    def test_revert_cli_no_commit_found(self, tmp_path: Path, capsys):
        (tmp_path / ".ai").mkdir()
        (tmp_path / ".ai" / "AUTONOMOUS_PLAN.md").write_text(PLAN_DONE, encoding="utf-8")
        from autonomous_forge.cli import main

        code = main([
            "revert", "AUTO-001",
            "--root", str(tmp_path),
            "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"),
        ])
        captured = capsys.readouterr()
        assert code == 1
        assert "FAILED" in captured.out

    def test_revert_cli_with_commit_override(self, tmp_path: Path, capsys):
        _init_real_repo(tmp_path)
        (tmp_path / ".ai").mkdir()
        (tmp_path / ".ai" / "AUTONOMOUS_PLAN.md").write_text(PLAN_DONE, encoding="utf-8")
        _git(["add", "-A"], tmp_path)
        _git(["commit", "-m", "add plan"], tmp_path)

        (tmp_path / "src" / "foo.py").write_text("changed\n", encoding="utf-8")
        _git(["add", "-A"], tmp_path)
        _git(["commit", "-m", "the target commit"], tmp_path)
        target_hash = _git(["rev-parse", "--short", "HEAD"], tmp_path).stdout.strip()

        from autonomous_forge.cli import main

        code = main([
            "revert", "AUTO-001",
            "--root", str(tmp_path),
            "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"),
            "--commit", target_hash,
        ])
        captured = capsys.readouterr()
        assert code == 0
        assert "REVERTED" in captured.out
