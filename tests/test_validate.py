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
