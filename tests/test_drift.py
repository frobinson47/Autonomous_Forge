from autonomous_forge.cli import main
from autonomous_forge.drift import (
    build_drift_report,
    check_readme_test_count_against_validation,
    collect_drift_signals,
)

PLAN_TWO_TASKS = """\
### AUTO-001 — First task
Priority: P1
Status: DONE

### AUTO-002 — Second task
Priority: P2
Status: TODO
"""


def test_no_drift_when_state_matches_plan():
    state = (
        "# State\n"
        "- Current task ID: AUTO-002 — Second task\n"
        "- Current task status: TODO\n"
        "- Last successful commit hash: abc123\n"
    )
    signals = collect_drift_signals(PLAN_TWO_TASKS, state_text=state)
    assert signals == []


def test_state_plan_status_mismatch():
    state = (
        "# State\n"
        "- Current task ID: AUTO-001 — First task\n"
        "- Current task status: TODO\n"
    )
    signals = collect_drift_signals(PLAN_TWO_TASKS, state_text=state)
    assert len(signals) == 1
    assert signals[0].category == "state-plan"
    assert signals[0].severity == "error"
    assert "TODO" in signals[0].message
    assert "DONE" in signals[0].message


def test_no_drift_when_plan_status_has_commit_annotation():
    plan = (
        "### AUTO-001 — First task\n"
        "Priority: P1\n"
        "Status: DONE — 70f89fd\n"
        "\n"
        "### AUTO-002 — Second task\n"
        "Priority: P2\n"
        "Status: TODO\n"
    )
    state = (
        "# State\n"
        "- Current task ID: AUTO-001 — First task\n"
        "- Current task status: DONE\n"
        "- Last successful commit hash: 70f89fd\n"
    )
    signals = collect_drift_signals(plan, state_text=state)
    assert signals == []


def test_state_references_missing_task():
    state = (
        "# State\n"
        "- Current task ID: AUTO-099 — Ghost task\n"
        "- Current task status: TODO\n"
    )
    signals = collect_drift_signals(PLAN_TWO_TASKS, state_text=state)
    assert len(signals) == 1
    assert signals[0].category == "state-plan"
    assert signals[0].severity == "error"
    assert "AUTO-099" in signals[0].message


def test_stale_commit_hash_detected():
    state = (
        "# State\n"
        "- Current task ID: AUTO-001 — First task\n"
        "- Current task status: DONE\n"
        "- Last successful commit hash: pending final commit lookup\n"
    )
    signals = collect_drift_signals(PLAN_TWO_TASKS, state_text=state)
    assert any(s.category == "stale-state" for s in signals)
    assert any("pending" in s.message.lower() for s in signals)


def test_state_matches_plan_with_four_digit_task_id():
    plan = (
        "### AUTO-1000 — Four digit task\n"
        "Priority: P1\n"
        "Status: TODO\n"
    )
    state = (
        "# State\n"
        "- Current task ID: AUTO-1000 — Four digit task\n"
        "- Current task status: TODO\n"
    )
    signals = collect_drift_signals(plan, state_text=state)
    assert signals == []


def test_changelog_accepts_four_digit_task_id():
    plan = (
        "### AUTO-1000 — Four digit task\n"
        "Priority: P1\n"
        "Status: DONE\n"
    )
    changelog = (
        "# Changelog\n"
        "## 2026-07-07 — AUTO-1000\n"
    )
    signals = collect_drift_signals(plan, changelog_text=changelog)
    assert signals == []


def test_changelog_references_unknown_task():
    changelog = (
        "# Changelog\n"
        "## 2026-07-07 — AUTO-001\n"
        "## 2026-07-07 — AUTO-999\n"
    )
    signals = collect_drift_signals(PLAN_TWO_TASKS, changelog_text=changelog)
    assert len(signals) == 1
    assert signals[0].category == "changelog-plan"
    assert "AUTO-999" in signals[0].message


def test_changelog_ignores_non_auto_headings():
    changelog = (
        "# Changelog\n"
        "## 2026-07-07 — Bootstrap\n"
        "## 2026-07-07 — Roadmap v2 planning\n"
    )
    signals = collect_drift_signals(PLAN_TWO_TASKS, changelog_text=changelog)
    assert signals == []


def test_policy_path_base_missing(tmp_path):
    policy = (
        "# Policy\n"
        "## Allowed paths\n"
        "- nonexistent_dir/**\n"
        "## Prohibited paths\n"
        "- .env\n"
        "## Human approval required\n"
        "- Adding network access.\n"
        "## Validation expectations\n"
        "- Run tests.\n"
    )
    signals = collect_drift_signals(
        PLAN_TWO_TASKS, policy_text=policy, root=tmp_path
    )
    assert any(
        s.category == "policy-repo" and "nonexistent_dir" in s.message
        for s in signals
    )


def test_policy_path_base_present(tmp_path):
    (tmp_path / "src").mkdir()
    policy = (
        "# Policy\n"
        "## Allowed paths\n"
        "- src/**\n"
        "## Prohibited paths\n"
        "- .env\n"
        "## Human approval required\n"
        "- Adding network access.\n"
        "## Validation expectations\n"
        "- Run tests.\n"
    )
    signals = collect_drift_signals(
        PLAN_TWO_TASKS, policy_text=policy, root=tmp_path
    )
    assert not any(s.category == "policy-repo" for s in signals)


def test_no_drift_with_no_optional_files():
    signals = collect_drift_signals(PLAN_TWO_TASKS)
    assert signals == []


def test_build_drift_report_no_drift():
    report = build_drift_report(PLAN_TWO_TASKS)
    assert "Drift report" in report
    assert "Mode: read-only" in report
    assert "no drift detected" in report


def test_build_drift_report_with_signals():
    state = (
        "# State\n"
        "- Current task ID: AUTO-099 — Ghost\n"
        "- Current task status: TODO\n"
        "- Last successful commit hash: pending\n"
    )
    report = build_drift_report(PLAN_TWO_TASKS, state_text=state)
    assert "signal(s) detected" in report
    assert "[error]" in report
    assert "[warn]" in report


def test_drift_cli_command(tmp_path, capsys):
    plan_path = tmp_path / ".ai" / "AUTONOMOUS_PLAN.md"
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text(PLAN_TWO_TASKS, encoding="utf-8")

    state_path = tmp_path / ".ai" / "AUTONOMOUS_STATE.md"
    state_path.write_text(
        "# State\n- Current task ID: AUTO-002 — Second task\n- Current task status: TODO\n",
        encoding="utf-8",
    )

    assert main([
        "drift",
        "--plan", str(plan_path),
        "--state", str(state_path),
        "--changelog", str(tmp_path / "missing_changelog.md"),
        "--policy", str(tmp_path / "missing_policy.md"),
        "--root", str(tmp_path),
    ]) == 0

    output = capsys.readouterr().out
    assert "Drift report" in output
    assert "Mode: read-only" in output


def test_drift_cli_missing_plan(tmp_path, capsys):
    result = main([
        "drift",
        "--plan", str(tmp_path / "nonexistent.md"),
    ])
    assert result == 2
    output = capsys.readouterr().out
    assert "Plan file not found" in output


class TestReadmeVsPlanAndState:
    PLAN = (
        "### AUTO-001 — First task\n"
        "Priority: P1\n"
        "Status: DONE\n"
        "\n"
        "### AUTO-002 — Second task\n"
        "Priority: P2\n"
        "Status: TODO\n"
    )

    def test_no_signal_when_counts_match(self):
        readme = "Status: (1/2 tasks done), tested (10 tests passing)."
        state = "- Validation commands and results: `python -m pytest` — 10 tests pass.\n"
        signals = collect_drift_signals(self.PLAN, state_text=state, readme_text=readme)
        assert signals == []

    def test_signal_when_task_counts_diverge(self):
        readme = "Status: (5/5 tasks done), tested (10 tests passing)."
        state = "- Validation commands and results: `python -m pytest` — 10 tests pass.\n"
        signals = collect_drift_signals(self.PLAN, state_text=state, readme_text=readme)
        assert len(signals) == 1
        assert signals[0].category == "readme-plan"
        assert "5/5" in signals[0].message
        assert "1/2" in signals[0].message

    def test_signal_when_test_counts_diverge(self):
        readme = "Status: (1/2 tasks done), tested (999 tests passing)."
        state = "- Validation commands and results: `python -m pytest` — 10 tests pass.\n"
        signals = collect_drift_signals(self.PLAN, state_text=state, readme_text=readme)
        assert len(signals) == 1
        assert signals[0].category == "readme-state"
        assert "999" in signals[0].message
        assert "10" in signals[0].message

    def test_no_check_when_readme_format_not_found(self):
        readme = "Status: still under construction."
        state = "- Validation commands and results: `python -m pytest` — 10 tests pass.\n"
        signals = collect_drift_signals(self.PLAN, state_text=state, readme_text=readme)
        assert signals == []

    def test_no_check_when_readme_text_not_provided(self):
        signals = collect_drift_signals(self.PLAN)
        assert signals == []


class TestReadmeTestCountAgainstValidation:
    def test_no_signal_when_counts_match(self):
        readme = "Status: (10 tests passing)."
        output = "....\n10 passed in 1.23s\n"
        assert check_readme_test_count_against_validation(readme, output) is None

    def test_signal_when_counts_diverge(self):
        readme = "Status: (999 tests passing)."
        output = "....\n10 passed in 1.23s\n"
        signal = check_readme_test_count_against_validation(readme, output)
        assert signal is not None
        assert signal.category == "readme-actual-tests"
        assert signal.severity == "warn"
        assert "999" in signal.message
        assert "10" in signal.message

    def test_no_signal_when_readme_format_not_found(self):
        readme = "Status: still under construction."
        output = "....\n10 passed in 1.23s\n"
        assert check_readme_test_count_against_validation(readme, output) is None

    def test_no_signal_when_output_not_pytest_shaped(self):
        readme = "Status: (10 tests passing)."
        output = "Build succeeded.\n"
        assert check_readme_test_count_against_validation(readme, output) is None

    def test_ignores_skipped_and_failed_counts_matches_on_passed_only(self):
        readme = "Status: (10 tests passing)."
        output = "....\n10 passed, 2 skipped in 1.23s\n"
        assert check_readme_test_count_against_validation(readme, output) is None
