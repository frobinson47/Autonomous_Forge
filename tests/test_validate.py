from autonomous_forge.cli import main
from autonomous_forge.validate import (
    ValidationResult,
    format_validation_result,
    run_validation,
)


def test_run_validation_passes_on_true(tmp_path):
    result = run_validation(
        tmp_path,
        command="python -c \"print('ok')\"",
        timestamp="2026-07-07T12:00:00+00:00",
    )
    assert result.passed is True
    assert result.exit_code == 0
    assert "ok" in result.stdout


def test_run_validation_fails_on_false(tmp_path):
    result = run_validation(
        tmp_path,
        command="python -c \"raise SystemExit(1)\"",
        timestamp="2026-07-07T12:00:00+00:00",
    )
    assert result.passed is False
    assert result.exit_code == 1


def test_run_validation_timeout(tmp_path):
    result = run_validation(
        tmp_path,
        command="python -c \"import time; time.sleep(10)\"",
        timeout_seconds=1,
        timestamp="2026-07-07T12:00:00+00:00",
    )
    assert result.passed is False
    assert "timed out" in result.stderr.lower()


def test_format_validation_result_passed():
    result = ValidationResult(
        command="pytest",
        exit_code=0,
        stdout="5 passed\n",
        stderr="",
        passed=True,
        timestamp="2026-07-07T12:00:00+00:00",
    )
    output = format_validation_result(result)
    assert "PASSED" in output
    assert "5 passed" in output


def test_format_validation_result_failed():
    result = ValidationResult(
        command="pytest",
        exit_code=1,
        stdout="2 failed\n",
        stderr="AssertionError\n",
        passed=False,
        timestamp="2026-07-07T12:00:00+00:00",
    )
    output = format_validation_result(result)
    assert "FAILED" in output
    assert "Errors:" in output


def test_validate_cli_passes(tmp_path, capsys):
    result = main([
        "validate",
        "--root", str(tmp_path),
        "--cmd", "python -c \"print('all good')\"",
    ])
    assert result == 0
    output = capsys.readouterr().out
    assert "PASSED" in output


def test_validate_cli_fails(tmp_path, capsys):
    result = main([
        "validate",
        "--root", str(tmp_path),
        "--cmd", "python -c \"raise SystemExit(1)\"",
    ])
    assert result == 1
    output = capsys.readouterr().out
    assert "FAILED" in output


class TestNeedsShell:
    def test_simple_command_does_not_need_shell(self):
        from autonomous_forge.validate import _needs_shell

        assert _needs_shell("python -m pytest") is False

    def test_pipe_needs_shell(self):
        from autonomous_forge.validate import _needs_shell

        assert _needs_shell("pytest | tee out.log") is True

    def test_chaining_needs_shell(self):
        from autonomous_forge.validate import _needs_shell

        assert _needs_shell("pytest && echo done") is True

    def test_metacharacter_inside_double_quotes_does_not_need_shell(self):
        from autonomous_forge.validate import _needs_shell

        assert _needs_shell('python -c "import sys; print(1)"') is False

    def test_metacharacter_inside_single_quotes_does_not_need_shell(self):
        from autonomous_forge.validate import _needs_shell

        assert _needs_shell("python -c 'import sys; print(1)'") is False

    def test_unquoted_semicolon_needs_shell(self):
        from autonomous_forge.validate import _needs_shell

        assert _needs_shell("pytest; echo done") is True


def test_run_validation_runs_simple_command_without_shell(tmp_path):
    result = run_validation(
        tmp_path,
        command="python -c \"print('no shell needed')\"",
        timestamp="2026-07-25T00:00:00+00:00",
    )
    assert result.passed is True
    assert "no shell needed" in result.stdout


def test_run_validation_blocks_shell_command_by_default(tmp_path):
    result = run_validation(
        tmp_path,
        command="python -c \"print(1)\" && python -c \"print(2)\"",
        timestamp="2026-07-25T00:00:00+00:00",
    )
    assert result.passed is False
    assert "--allow-shell-command" in result.stderr


def test_run_validation_allow_shell_command_override_runs_it(tmp_path):
    result = run_validation(
        tmp_path,
        command="python -c \"print(1)\" && python -c \"print(2)\"",
        timestamp="2026-07-25T00:00:00+00:00",
        allow_shell_command=True,
    )
    assert result.passed is True
    assert "1" in result.stdout
    assert "2" in result.stdout


def test_run_validation_semicolon_inside_quotes_does_not_need_shell(tmp_path):
    result = run_validation(
        tmp_path,
        command="python -c \"import sys; print('ok')\"",
        timestamp="2026-07-25T00:00:00+00:00",
    )
    assert result.passed is True
    assert "ok" in result.stdout


def test_validate_cli_blocked_shell_command_without_flag(tmp_path, capsys):
    result = main([
        "validate",
        "--root", str(tmp_path),
        "--cmd", "python -c \"print(1)\" && python -c \"print(2)\"",
    ])
    assert result == 1
    output = capsys.readouterr().out
    assert "FAILED" in output
    assert "--allow-shell-command" in output


def test_validate_cli_allow_shell_command_flag(tmp_path, capsys):
    result = main([
        "validate",
        "--root", str(tmp_path),
        "--cmd", "python -c \"print(1)\" && python -c \"print(2)\"",
        "--allow-shell-command",
    ])
    assert result == 0
    output = capsys.readouterr().out
    assert "PASSED" in output
