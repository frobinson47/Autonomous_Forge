"""Tests for forge check — combined verification."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from autonomous_forge.check import CheckResult, execute_check, format_check_result


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
