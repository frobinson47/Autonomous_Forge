from autonomous_forge.cli import main
from autonomous_forge.diffcheck import build_diff_report, check_diff_against_policy


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


def test_diffcheck_cli_command(tmp_path, capsys):
    result = main(["diff-check", "--root", str(tmp_path)])
    assert result == 0
    output = capsys.readouterr().out
    assert "Diff check report" in output
