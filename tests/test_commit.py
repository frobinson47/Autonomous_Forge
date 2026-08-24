"""Tests for the safe auto-commit module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from autonomous_forge.commit import (
    CommitPreFlight,
    CommitResult,
    execute_commit,
    format_commit_result,
    format_pre_flight,
    run_pre_flight,
)
from autonomous_forge.diffcheck import GitCommandError

_LINT_CLEAN_TAIL = """\
Why it matters: Test fixture.
Scope: Test fixture.
Expected files or areas: tests.
Acceptance criteria: Passes.
Validation: N/A.
Risks or assumptions: None.
Notes: Test fixture.
"""

PLAN_WITH_TODO = f"""\
# Roadmap

### AUTO-001 — Build widget
Priority: P1
Status: TODO

Goal: Build a widget.
{_LINT_CLEAN_TAIL}"""

PLAN_ALL_DONE = f"""\
# Roadmap

### AUTO-001 — Build widget
Priority: P1
Status: DONE

Goal: Build a widget.
{_LINT_CLEAN_TAIL}"""

PLAN_WITH_APPROVAL = f"""\
# Roadmap

### AUTO-001 — Add network call
Priority: P1
Status: TODO
Approval needed: Adding network access.

Goal: Build a widget that calls a network API.
{_LINT_CLEAN_TAIL}"""

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

    @patch("autonomous_forge.commit.get_changed_files", side_effect=GitCommandError("boom"))
    def test_git_failure_blocks_with_distinct_message(self, mock_git, tmp_path):
        _setup(tmp_path)
        pf = run_pre_flight(root=tmp_path, validate=False)
        assert not pf.safe
        assert "Could not determine changed files" in pf.block_reason
        assert "No changed files" not in pf.block_reason

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

    @patch("autonomous_forge.commit.get_changed_files", return_value=["src/foo.py"])
    def test_missing_policy_blocks_by_default(self, mock_git, tmp_path):
        (tmp_path / ".ai").mkdir()
        (tmp_path / ".ai/AUTONOMOUS_PLAN.md").write_text(PLAN_WITH_TODO, encoding="utf-8")
        pf = run_pre_flight(root=tmp_path, validate=False)
        assert not pf.safe
        assert "missing" in pf.block_reason
        assert "--no-policy-required" in pf.block_reason

    @patch("autonomous_forge.commit.get_changed_files", return_value=["src/foo.py"])
    def test_missing_policy_override_allows_commit(self, mock_git, tmp_path):
        (tmp_path / ".ai").mkdir()
        (tmp_path / ".ai/AUTONOMOUS_PLAN.md").write_text(PLAN_WITH_TODO, encoding="utf-8")
        pf = run_pre_flight(root=tmp_path, validate=False, require_policy=False)
        assert pf.safe

    @patch("autonomous_forge.commit.get_changed_files", return_value=["src/foo.py"])
    def test_lint_diagnostic_blocks_commit_by_default(self, mock_git, tmp_path):
        bad_plan = "### AUTO-001 — Build widget\nPriority: P1\nStatus: TODO\nGoal: Test.\n"
        _setup(tmp_path, plan=bad_plan)
        pf = run_pre_flight(root=tmp_path, validate=False)
        assert not pf.safe
        assert "forge lint-plan failed" in pf.block_reason
        assert "--no-lint-required" in pf.block_reason

    @patch("autonomous_forge.commit.get_changed_files", return_value=["src/foo.py"])
    def test_no_lint_required_override_allows_commit(self, mock_git, tmp_path):
        bad_plan = "### AUTO-001 — Build widget\nPriority: P1\nStatus: TODO\nGoal: Test.\n"
        _setup(tmp_path, plan=bad_plan)
        pf = run_pre_flight(root=tmp_path, validate=False, require_lint_pass=False)
        assert pf.safe

    @patch("autonomous_forge.commit.get_changed_files", return_value=["src/foo.py"])
    def test_malformed_policy_blocks_by_default(self, mock_git, tmp_path):
        _setup(tmp_path, policy="## Allowed paths\n- `src/**`\n")
        pf = run_pre_flight(root=tmp_path, validate=False)
        assert not pf.safe
        assert "malformed" in pf.block_reason

    @patch("autonomous_forge.commit.get_changed_files", return_value=["random.txt"])
    def test_not_allowed_file_blocks_by_default(self, mock_git, tmp_path):
        _setup(tmp_path)
        pf = run_pre_flight(root=tmp_path, validate=False)
        assert not pf.safe
        assert "random.txt" in pf.block_reason
        assert "--advisory-paths" in pf.block_reason

    @patch("autonomous_forge.commit.get_changed_files", return_value=["random.txt"])
    def test_advisory_paths_override_allows_commit(self, mock_git, tmp_path):
        _setup(tmp_path)
        pf = run_pre_flight(root=tmp_path, validate=False, advisory_paths=True)
        assert pf.safe
        assert any("not-allowed" in v for v in pf.violations)

    @patch("autonomous_forge.commit.get_changed_files", return_value=["src/foo.py"])
    def test_approval_needed_blocks_without_record(self, mock_git, tmp_path):
        _setup(tmp_path, plan=PLAN_WITH_APPROVAL)
        pf = run_pre_flight(root=tmp_path, validate=False)
        assert not pf.safe
        assert "requires human approval" in pf.block_reason
        assert "forge approve AUTO-001" in pf.block_reason

    @patch("autonomous_forge.commit.get_changed_files", return_value=["src/foo.py"])
    def test_approval_needed_allows_commit_once_recorded(self, mock_git, tmp_path):
        from autonomous_forge.approvals import record_approval

        _setup(tmp_path, plan=PLAN_WITH_APPROVAL)
        record_approval("AUTO-001", "Adding network access.", root=tmp_path)
        pf = run_pre_flight(root=tmp_path, validate=False)
        assert pf.safe


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

    @patch("autonomous_forge.commit.get_changed_files", return_value=["src/foo.py"])
    def test_check_only_blocked_by_missing_policy(self, mock_git, tmp_path, capsys):
        (tmp_path / ".ai").mkdir()
        (tmp_path / ".ai/AUTONOMOUS_PLAN.md").write_text(PLAN_WITH_TODO, encoding="utf-8")
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
        assert "missing" in captured.out

    @patch("autonomous_forge.commit.get_changed_files", return_value=["src/foo.py"])
    def test_check_only_no_policy_required_override(self, mock_git, tmp_path, capsys):
        (tmp_path / ".ai").mkdir()
        (tmp_path / ".ai/AUTONOMOUS_PLAN.md").write_text(PLAN_WITH_TODO, encoding="utf-8")
        from autonomous_forge.cli import main

        code = main([
            "commit", "--check-only", "--no-validate", "--no-policy-required",
            "--root", str(tmp_path),
            "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"),
            "--policy", str(tmp_path / ".forge/policy.md"),
        ])
        captured = capsys.readouterr()
        assert code == 0
        assert "SAFE" in captured.out

    @patch("autonomous_forge.commit.get_changed_files", return_value=["src/foo.py"])
    def test_forge_approve_unblocks_check_only(self, mock_git, tmp_path, capsys):
        _setup(tmp_path, plan=PLAN_WITH_APPROVAL)
        from autonomous_forge.cli import main

        code = main([
            "commit", "--check-only", "--no-validate",
            "--root", str(tmp_path),
            "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"),
            "--policy", str(tmp_path / ".forge/policy.md"),
        ])
        assert code == 1
        capsys.readouterr()

        code = main([
            "approve", "AUTO-001", "Adding network access.",
            "--root", str(tmp_path),
        ])
        approve_out = capsys.readouterr().out
        assert code == 0
        assert "AUTO-001" in approve_out

        code = main([
            "commit", "--check-only", "--no-validate",
            "--root", str(tmp_path),
            "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"),
            "--policy", str(tmp_path / ".forge/policy.md"),
        ])
        captured = capsys.readouterr()
        assert code == 0
        assert "SAFE" in captured.out

    @patch("autonomous_forge.commit.get_changed_files", return_value=["src/foo.py"])
    def test_check_only_blocked_by_lint_diagnostic(self, mock_git, tmp_path, capsys):
        bad_plan = "### AUTO-001 — Build widget\nPriority: P1\nStatus: TODO\nGoal: Test.\n"
        _setup(tmp_path, plan=bad_plan)
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
        assert "forge lint-plan failed" in captured.out

    @patch("autonomous_forge.commit.get_changed_files", return_value=["src/foo.py"])
    def test_check_only_no_lint_required_override(self, mock_git, tmp_path, capsys):
        bad_plan = "### AUTO-001 — Build widget\nPriority: P1\nStatus: TODO\nGoal: Test.\n"
        _setup(tmp_path, plan=bad_plan)
        from autonomous_forge.cli import main

        code = main([
            "commit", "--check-only", "--no-validate", "--no-lint-required",
            "--root", str(tmp_path),
            "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"),
            "--policy", str(tmp_path / ".forge/policy.md"),
        ])
        captured = capsys.readouterr()
        assert code == 0
        assert "SAFE" in captured.out

    @patch("autonomous_forge.commit.get_changed_files", return_value=["random.txt"])
    def test_check_only_blocked_by_not_allowed_path(self, mock_git, tmp_path, capsys):
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
        assert "random.txt" in captured.out

    @patch("autonomous_forge.commit.get_changed_files", return_value=["random.txt"])
    def test_check_only_advisory_paths_override(self, mock_git, tmp_path, capsys):
        _setup(tmp_path)
        from autonomous_forge.cli import main

        code = main([
            "commit", "--check-only", "--no-validate", "--advisory-paths",
            "--root", str(tmp_path),
            "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"),
            "--policy", str(tmp_path / ".forge/policy.md"),
        ])
        captured = capsys.readouterr()
        assert code == 0
        assert "SAFE" in captured.out


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git"] + args, cwd=cwd, check=True, capture_output=True, text=True)


def _init_real_repo(tmp_path: Path) -> None:
    """Set up a real (isolated, tmp_path-local) git repo for changelog integration tests.

    find_newly_done_tasks compares the working-tree plan against HEAD via a
    real `git show`, so this is more faithful here than mocking subprocess.
    """
    _git(["init"], tmp_path)
    _git(["config", "user.email", "test@example.com"], tmp_path)
    _git(["config", "user.name", "Test"], tmp_path)
    (tmp_path / ".ai").mkdir()
    (tmp_path / ".ai/AUTONOMOUS_PLAN.md").write_text(PLAN_WITH_TODO, encoding="utf-8")
    (tmp_path / ".ai/AUTONOMOUS_CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    (tmp_path / ".forge").mkdir()
    (tmp_path / ".forge/policy.md").write_text(POLICY, encoding="utf-8")
    _git(["add", "-A"], tmp_path)
    _git(["commit", "-m", "initial"], tmp_path)


class TestExecuteCommitChangelogIntegration:
    @patch("autonomous_forge.commit.get_changed_files", return_value=["src/foo.py"])
    def test_changelog_line_lands_in_same_commit(self, mock_git, tmp_path):
        _init_real_repo(tmp_path)
        (tmp_path / ".ai/AUTONOMOUS_PLAN.md").write_text(PLAN_ALL_DONE, encoding="utf-8")
        (tmp_path / "src").mkdir()
        (tmp_path / "src/foo.py").write_text("# code\n", encoding="utf-8")
        _git(["add", "-A"], tmp_path)

        result = execute_commit(root=tmp_path, validate=False)

        assert result.committed
        assert result.changelog_task_ids == ("AUTO-001",)

        changelog_text = (tmp_path / ".ai/AUTONOMOUS_CHANGELOG.md").read_text(encoding="utf-8")
        assert "AUTO-001 — Build widget (DONE)" in changelog_text

        # The changelog line must be part of THIS commit, not left dangling.
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=tmp_path,
            capture_output=True, text=True,
        )
        assert status.stdout.strip() == ""

    @patch("autonomous_forge.commit.get_changed_files", return_value=["src/foo.py"])
    def test_no_changelog_touch_when_no_task_flips_to_done(self, mock_git, tmp_path):
        _init_real_repo(tmp_path)
        (tmp_path / "src").mkdir()
        (tmp_path / "src/foo.py").write_text("# code\n", encoding="utf-8")
        _git(["add", "-A"], tmp_path)

        result = execute_commit(root=tmp_path, validate=False)

        assert result.committed
        assert result.changelog_task_ids == ()
        changelog_text = (tmp_path / ".ai/AUTONOMOUS_CHANGELOG.md").read_text(encoding="utf-8")
        assert changelog_text == "# Changelog\n"

    def test_changelog_path_blocked_by_policy_after_staging(self, tmp_path):
        # POLICY (module-level) allows only src/** and tests/** — .ai/** is
        # not-allowed. The plan's DONE flip is left unstaged (matching the
        # real forge-mark-then-commit workflow: find_newly_done_tasks reads
        # the working tree directly, not the index), so the ORIGINAL
        # pre-flight only sees src/foo.py and reports safe. Staging the
        # changelog afterward must still be caught by the post-staging
        # re-check (AUTO-061 / SEC-005), not silently committed.
        _init_real_repo(tmp_path)
        (tmp_path / ".ai/AUTONOMOUS_PLAN.md").write_text(PLAN_ALL_DONE, encoding="utf-8")
        (tmp_path / "src").mkdir()
        (tmp_path / "src/foo.py").write_text("# code\n", encoding="utf-8")
        _git(["add", "src/foo.py"], tmp_path)

        result = execute_commit(root=tmp_path, validate=False)

        assert not result.committed
        assert "Changelog update violates policy" in result.message
        assert ".ai" in result.message or "AUTONOMOUS_CHANGELOG" in result.message

        # Nothing was actually committed.
        log = subprocess.run(
            ["git", "log", "--oneline"], cwd=tmp_path,
            capture_output=True, text=True,
        )
        assert log.stdout.count("\n") == 1  # only the "initial" commit

    def test_git_add_failure_for_changelog_blocks(self, tmp_path):
        _init_real_repo(tmp_path)
        (tmp_path / ".ai/AUTONOMOUS_PLAN.md").write_text(PLAN_ALL_DONE, encoding="utf-8")
        (tmp_path / "src").mkdir()
        (tmp_path / "src/foo.py").write_text("# code\n", encoding="utf-8")
        _git(["add", "src/foo.py"], tmp_path)

        with patch("autonomous_forge.commit._git_add", return_value=False):
            result = execute_commit(root=tmp_path, validate=False)

        assert not result.committed
        assert "git add failed" in result.message
