from unittest.mock import patch

from autonomous_forge.cli import main
from autonomous_forge.diffcheck import (
    GitCommandError,
    build_diff_report,
    check_diff_against_policy,
    get_changed_files,
)

POLICY_VALID = """\
# Policy

## Allowed paths

- src/**
- tests/**
- README.md

## Prohibited paths

- .env
- .env.*
- **/*.key

## Human approval required

- Adding network access.

## Validation expectations

- Run tests.
"""


def test_no_violations_for_allowed_files():
    violations = check_diff_against_policy(
        ["src/main.py", "tests/test_main.py", "README.md"],
        POLICY_VALID,
    )
    assert violations == []


def test_prohibited_file_detected():
    violations = check_diff_against_policy([".env"], POLICY_VALID)
    assert len(violations) == 1
    assert violations[0].rule == "prohibited"
    assert ".env" in violations[0].path


def test_prohibited_pattern_matches():
    violations = check_diff_against_policy(["certs/server.key"], POLICY_VALID)
    assert any(v.rule == "prohibited" for v in violations)


def test_not_allowed_file_detected():
    violations = check_diff_against_policy(["config/prod.yml"], POLICY_VALID)
    assert any(v.rule == "not-allowed" for v in violations)


def test_no_changes_report():
    report = build_diff_report([], POLICY_VALID)
    assert "nothing to check" in report


def test_compliant_changes_report():
    report = build_diff_report(["src/app.py"], POLICY_VALID)
    assert "all changes comply" in report


def test_violation_report():
    report = build_diff_report([".env", "src/app.py"], POLICY_VALID)
    assert "violation(s)" in report
    assert "[prohibited]" in report


def test_missing_policy_report():
    report = build_diff_report(["src/app.py"], None)
    assert "not found" in report


@patch("autonomous_forge.diffcheck.get_changed_files", return_value=[])
def test_diffcheck_cli_command(mock_git, tmp_path, capsys):
    result = main(["diff-check", "--root", str(tmp_path)])
    assert result == 0
    output = capsys.readouterr().out
    assert "Diff check report" in output


def test_diffcheck_cli_command_not_a_git_repo_exits_1(tmp_path, capsys):
    # tmp_path is a real directory but not a git repository, so the
    # underlying `git diff` calls fail — this must be reported as an
    # error, not silently treated as "no changes" (AUTO-060 / SEC-008).
    result = main(["diff-check", "--root", str(tmp_path)])
    assert result == 1
    output = capsys.readouterr().out
    assert "could not inspect changes" in output


def test_get_changed_files_raises_on_git_failure(tmp_path):
    try:
        get_changed_files(tmp_path)
    except GitCommandError:
        pass
    else:
        raise AssertionError("expected GitCommandError for a non-git directory")
