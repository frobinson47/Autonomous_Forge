"""Tests for forge check — combined verification."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from autonomous_forge.check import CheckResult, execute_check, format_check_result
from autonomous_forge.diffcheck import GitCommandError

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
"""

PLAN_BAD = """\
# Roadmap

### AUTO-001 — Build widget
Priority: P1

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


def _setup(tmp_path: Path, plan: str = PLAN):
    (tmp_path / ".ai").mkdir()
    (tmp_path / ".ai/AUTONOMOUS_PLAN.md").write_text(plan, encoding="utf-8")
    (tmp_path / ".ai/AUTONOMOUS_STATE.md").write_text("- Current task: none\n", encoding="utf-8")
    (tmp_path / ".ai/AUTONOMOUS_CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    (tmp_path / ".forge").mkdir()
    (tmp_path / ".forge/policy.md").write_text(POLICY, encoding="utf-8")


class TestExecuteCheck:
    @patch("autonomous_forge.check.get_changed_files", return_value=[])
    def test_all_pass_no_validate(self, mock_git, tmp_path):
        _setup(tmp_path)
        result = execute_check(root=tmp_path, validate=False)
        assert result.lint_ok is True
        assert result.diff_ok is True
        assert result.validation_ok is None
        assert result.all_passed is True

    @patch("autonomous_forge.check.get_changed_files", return_value=[])
    def test_lint_failure(self, mock_git, tmp_path):
        _setup(tmp_path, plan=PLAN_BAD)
        result = execute_check(root=tmp_path, validate=False)
        assert result.lint_ok is False
        assert len(result.lint_diagnostics) > 0
        assert result.all_passed is False

    @patch("autonomous_forge.check.get_changed_files", return_value=[".env"])
    def test_diff_violation(self, mock_git, tmp_path):
        _setup(tmp_path)
        result = execute_check(root=tmp_path, validate=False)
        assert result.diff_ok is False
        assert len(result.diff_violations) > 0
        assert result.all_passed is False

    @patch("autonomous_forge.check.get_changed_files", return_value=[])
    def test_missing_policy_fails_closed_by_default(self, mock_git, tmp_path):
        _setup(tmp_path)
        (tmp_path / ".forge/policy.md").unlink()
        result = execute_check(root=tmp_path, validate=False)
        assert result.diff_ok is False
        assert any("missing" in v.lower() for v in result.diff_violations)
        assert result.all_passed is False

    @patch("autonomous_forge.check.get_changed_files", return_value=[])
    def test_missing_policy_override_skips_check(self, mock_git, tmp_path):
        _setup(tmp_path)
        (tmp_path / ".forge/policy.md").unlink()
        result = execute_check(root=tmp_path, validate=False, require_policy=False)
        assert result.diff_ok is True
        assert result.all_passed is True

    @patch("autonomous_forge.check.get_changed_files", return_value=[])
    def test_malformed_policy_fails_closed(self, mock_git, tmp_path):
        _setup(tmp_path)
        (tmp_path / ".forge/policy.md").write_text(
            "# Repository Policy\n\nnot a heading or a bullet\n", encoding="utf-8"
        )
        result = execute_check(root=tmp_path, validate=False)
        assert result.diff_ok is False
        assert any("malformed" in v.lower() for v in result.diff_violations)
        assert result.all_passed is False

    @patch("autonomous_forge.check.get_changed_files", return_value=[])
    def test_unreadable_policy_fails_closed(self, mock_git, tmp_path):
        _setup(tmp_path)
        (tmp_path / ".forge/policy.md").unlink()
        (tmp_path / ".forge/policy.md").mkdir()
        result = execute_check(root=tmp_path, validate=False)
        assert result.diff_ok is False
        assert any("could not read policy file" in v.lower() for v in result.diff_violations)
        assert result.all_passed is False

    @patch("autonomous_forge.check.get_changed_files", side_effect=GitCommandError("boom"))
    def test_git_failure_fails_diff_check_closed(self, mock_git, tmp_path):
        _setup(tmp_path)
        result = execute_check(root=tmp_path, validate=False)
        assert result.diff_ok is False
        assert any("could not determine changed files" in v.lower() for v in result.diff_violations)
        assert result.all_passed is False

    @patch("autonomous_forge.check.check_diff_against_policy")
    @patch("autonomous_forge.check.get_changed_files", return_value=["src/x.py"])
    def test_unexpected_diff_check_exception_is_not_swallowed(
        self, mock_git, mock_diff, tmp_path
    ):
        _setup(tmp_path)
        mock_diff.side_effect = RuntimeError("boom")
        try:
            execute_check(root=tmp_path, validate=False)
        except RuntimeError as exc:
            assert "boom" in str(exc)
        else:
            raise AssertionError("expected RuntimeError to propagate, not be swallowed")

    @patch("autonomous_forge.check.get_changed_files", return_value=[])
    def test_missing_plan(self, mock_git, tmp_path):
        (tmp_path / ".forge").mkdir(exist_ok=True)
        result = execute_check(root=tmp_path, validate=False)
        assert result.lint_ok is False
        assert "not found" in result.lint_diagnostics[0].lower()

    @patch("autonomous_forge.check.get_changed_files", return_value=[])
    @patch("autonomous_forge.check.run_validation")
    def test_validation_pass(self, mock_val, mock_git, tmp_path):
        _setup(tmp_path)
        from autonomous_forge.validate import ValidationResult
        mock_val.return_value = ValidationResult(
            passed=True, command="pytest", stdout="ok", stderr="",
            exit_code=0, timestamp="2026-01-01T00:00:00+00:00",
        )
        result = execute_check(root=tmp_path, validate=True)
        assert result.validation_ok is True
        assert result.all_passed is True

    @patch("autonomous_forge.check.get_changed_files", return_value=[])
    @patch("autonomous_forge.check.run_validation")
    def test_readme_actual_test_count_signal_surfaces_in_drift(self, mock_val, mock_git, tmp_path):
        _setup(tmp_path)
        (tmp_path / "README.md").write_text("Status: (999 tests passing).\n", encoding="utf-8")
        from autonomous_forge.validate import ValidationResult
        mock_val.return_value = ValidationResult(
            passed=True, command="pytest", stdout="10 passed in 1.23s", stderr="",
            exit_code=0, timestamp="2026-01-01T00:00:00+00:00",
        )
        result = execute_check(root=tmp_path, validate=True)
        assert result.validation_ok is True
        assert any("readme-actual-tests" in s for s in result.drift_signals)
        assert any("999" in s and "10" in s for s in result.drift_signals)
        # Non-blocking: this signal alone must not fail the run.
        assert result.drift_ok is True
        assert result.all_passed is True

    @patch("autonomous_forge.check.get_changed_files", return_value=[])
    @patch("autonomous_forge.check.run_validation")
    def test_validation_fail(self, mock_val, mock_git, tmp_path):
        _setup(tmp_path)
        from autonomous_forge.validate import ValidationResult
        mock_val.return_value = ValidationResult(
            passed=False, command="pytest", stdout="FAILED", stderr="",
            exit_code=1, timestamp="2026-01-01T00:00:00+00:00",
        )
        result = execute_check(root=tmp_path, validate=True)
        assert result.validation_ok is False
        assert result.all_passed is False

    @patch("autonomous_forge.check.get_changed_files", return_value=[])
    @patch("autonomous_forge.check.run_validation")
    def test_validation_fail_includes_stderr_in_output(self, mock_val, mock_git, tmp_path):
        _setup(tmp_path)
        from autonomous_forge.validate import ValidationResult
        mock_val.return_value = ValidationResult(
            passed=False, command="pytest", stdout="1 failed",
            stderr="Traceback (most recent call last):\nAssertionError",
            exit_code=1, timestamp="2026-01-01T00:00:00+00:00",
        )
        result = execute_check(root=tmp_path, validate=True)
        assert "1 failed" in result.validation_output
        assert "AssertionError" in result.validation_output

    @patch("autonomous_forge.check.get_changed_files", return_value=[])
    def test_stale_readme_surfaces_as_warning_not_failure(self, mock_git, tmp_path):
        _setup(tmp_path)
        (tmp_path / "README.md").write_text(
            "Status: (99/99 tasks done), tested (12345 tests passing).\n",
            encoding="utf-8",
        )
        (tmp_path / ".ai/AUTONOMOUS_STATE.md").write_text(
            "- Validation commands and results: `python -m pytest` — 1 tests pass.\n",
            encoding="utf-8",
        )
        result = execute_check(root=tmp_path, validate=False)
        assert result.drift_ok is True  # warn severity — does not fail the check
        assert any("readme" in msg.lower() for msg in result.drift_signals)
        assert result.all_passed is True


class TestFormatCheckResult:
    def test_format_all_pass(self):
        r = CheckResult(
            lint_ok=True, lint_diagnostics=(),
            drift_ok=True, drift_signals=(),
            diff_ok=True, diff_violations=(),
            validation_ok=True, validation_output="",
            all_passed=True,
        )
        text = format_check_result(r)
        assert "ALL PASSED" in text
        assert "Lint: PASS" in text

    def test_format_failures(self):
        r = CheckResult(
            lint_ok=False, lint_diagnostics=("line 1: bad",),
            drift_ok=True, drift_signals=(),
            diff_ok=False, diff_violations=(".env",),
            validation_ok=None, validation_output="",
            all_passed=False,
        )
        text = format_check_result(r)
        assert "ISSUES FOUND" in text
        assert "Lint: FAIL" in text
        assert ".env" in text

    def test_format_validation_failure_includes_output_tail(self):
        r = CheckResult(
            lint_ok=True, lint_diagnostics=(),
            drift_ok=True, drift_signals=(),
            diff_ok=True, diff_violations=(),
            validation_ok=False,
            validation_output="collecting...\nFAILED tests/test_foo.py::test_bar\nAssertionError: boom",
            all_passed=False,
        )
        text = format_check_result(r)
        assert "Validation: FAIL" in text
        assert "FAILED tests/test_foo.py::test_bar" in text
        assert "AssertionError: boom" in text

    def test_format_validation_pass_omits_output(self):
        r = CheckResult(
            lint_ok=True, lint_diagnostics=(),
            drift_ok=True, drift_signals=(),
            diff_ok=True, diff_violations=(),
            validation_ok=True,
            validation_output="5 passed",
            all_passed=True,
        )
        text = format_check_result(r)
        assert "Validation: PASS" in text
        assert "5 passed" not in text


class TestCheckCLI:
    @patch("autonomous_forge.check.get_changed_files", return_value=[])
    def test_check_cli_pass(self, mock_git, tmp_path, capsys):
        _setup(tmp_path)
        from autonomous_forge.cli import main

        code = main([
            "check",
            "--root", str(tmp_path),
            "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"),
            "--policy", str(tmp_path / ".forge/policy.md"),
            "--no-validate",
        ])
        captured = capsys.readouterr()
        assert code == 0
        assert "ALL PASSED" in captured.out

    @patch("autonomous_forge.check.get_changed_files", return_value=[".env"])
    def test_check_cli_fail(self, mock_git, tmp_path, capsys):
        _setup(tmp_path)
        from autonomous_forge.cli import main

        code = main([
            "check",
            "--root", str(tmp_path),
            "--plan", str(tmp_path / ".ai/AUTONOMOUS_PLAN.md"),
            "--policy", str(tmp_path / ".forge/policy.md"),
            "--no-validate",
        ])
        assert code == 1
