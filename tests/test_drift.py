from autonomous_forge.cli import main
from autonomous_forge.drift import build_drift_report, collect_drift_signals


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
