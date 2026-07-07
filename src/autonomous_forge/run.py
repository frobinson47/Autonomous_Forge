"""Execute one autonomous improvement cycle and record the outcome."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from autonomous_forge.diffcheck import check_diff_against_policy, get_changed_files
from autonomous_forge.drift import collect_drift_signals
from autonomous_forge.plan import (
    PlanTask,
    parse_plan_tasks,
    select_eligible_task,
)
from autonomous_forge.policy import PolicyParseError, parse_repository_policy
from autonomous_forge.validate import run_validation


@dataclass(frozen=True)
class RunOutcome:
    """Complete outcome of one autonomous run cycle."""

    timestamp: str
    selected_task: PlanTask | None
    validation_passed: bool | None
    validation_command: str
    validation_output: str
    diff_violations: int
    diff_details: tuple[str, ...]
    drift_signals: int
    changed_files: tuple[str, ...]
    policy_status: str
    blocked: bool
    block_reason: str


_SUMMARY_DIR = ".forge/runs"


def _safe_read(path: Path) -> str | None:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def execute_run(
    root: Path = Path("."),
    plan_path: Path | None = None,
    state_path: Path | None = None,
    changelog_path: Path | None = None,
    policy_path: Path | None = None,
    validate: bool = True,
    validate_command: str | None = None,
    validate_timeout: int = 300,
    timestamp: str | None = None,
    dry_run: bool = False,
) -> RunOutcome:
    """Execute one autonomous cycle: select, validate, diff-check, record."""
    plan_p = plan_path or (root / ".ai/AUTONOMOUS_PLAN.md")
    state_p = state_path or (root / ".ai/AUTONOMOUS_STATE.md")
    changelog_p = changelog_path or (root / ".ai/AUTONOMOUS_CHANGELOG.md")
    policy_p = policy_path or (root / ".forge/policy.md")

    ts = timestamp or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    plan_text = plan_p.read_text(encoding="utf-8")
    state_text = _safe_read(state_p)
    changelog_text = _safe_read(changelog_p)
    policy_text = _safe_read(policy_p)

    tasks = parse_plan_tasks(plan_text)
    selected_task = select_eligible_task(tasks)

    policy_status = "not found"
    if policy_text is not None:
        try:
            parse_repository_policy(policy_text)
            policy_status = "present and readable"
        except PolicyParseError as exc:
            policy_status = f"malformed: {exc}"

    drift_signals_list = collect_drift_signals(
        plan_text, state_text, changelog_text, policy_text, root
    )
    drift_count = len(drift_signals_list)

    if selected_task is None:
        return RunOutcome(
            timestamp=ts,
            selected_task=None,
            validation_passed=None,
            validation_command="",
            validation_output="",
            diff_violations=0,
            diff_details=(),
            drift_signals=drift_count,
            changed_files=(),
            policy_status=policy_status,
            blocked=False,
            block_reason="No eligible TODO task.",
        )

    if drift_count > 0:
        error_drifts = [s for s in drift_signals_list if s.severity == "error"]
        if error_drifts:
            return RunOutcome(
                timestamp=ts,
                selected_task=selected_task,
                validation_passed=None,
                validation_command="",
                validation_output="",
                diff_violations=0,
                diff_details=(),
                drift_signals=drift_count,
                changed_files=(),
                policy_status=policy_status,
                blocked=True,
                block_reason=f"Metadata drift detected: {error_drifts[0].message}",
            )

    changed_files = get_changed_files(root)

    diff_violations_list = []
    if policy_text and changed_files:
        diff_violations_list = check_diff_against_policy(changed_files, policy_text)

    prohibited = [v for v in diff_violations_list if v.rule == "prohibited"]
    if prohibited:
        return RunOutcome(
            timestamp=ts,
            selected_task=selected_task,
            validation_passed=None,
            validation_command="",
            validation_output="",
            diff_violations=len(diff_violations_list),
            diff_details=tuple(f"[{v.rule}] {v.path}: {v.message}" for v in diff_violations_list),
            drift_signals=drift_count,
            changed_files=tuple(changed_files),
            policy_status=policy_status,
            blocked=True,
            block_reason=f"Prohibited file(s) changed: {', '.join(v.path for v in prohibited)}",
        )

    validation_passed = None
    validation_command = ""
    validation_output = ""

    if validate and not dry_run:
        val_result = run_validation(
            root,
            command=validate_command,
            policy_path=policy_p,
            timeout_seconds=validate_timeout,
            timestamp=ts,
        )
        validation_passed = val_result.passed
        validation_command = val_result.command
        output_lines = val_result.stdout.strip().splitlines()
        if len(output_lines) > 10:
            validation_output = "\n".join(output_lines[-10:])
        else:
            validation_output = val_result.stdout.strip()
        if val_result.stderr.strip():
            validation_output += "\n" + val_result.stderr.strip()
    elif dry_run:
        validation_command = "skipped (dry run)"
        validation_output = "dry run — validation not executed"

    return RunOutcome(
        timestamp=ts,
        selected_task=selected_task,
        validation_passed=validation_passed,
        validation_command=validation_command,
        validation_output=validation_output,
        diff_violations=len(diff_violations_list),
        diff_details=tuple(f"[{v.rule}] {v.path}: {v.message}" for v in diff_violations_list),
        drift_signals=drift_count,
        changed_files=tuple(changed_files),
        policy_status=policy_status,
        blocked=False,
        block_reason="",
    )


def format_run_outcome(outcome: RunOutcome) -> str:
    """Format a run outcome as a human-readable report."""
    lines = [
        "Forge run report",
        f"Timestamp: {outcome.timestamp}",
    ]

    if outcome.selected_task:
        lines.append(
            f"Selected task: {outcome.selected_task.task_id} — {outcome.selected_task.title}"
        )
    else:
        lines.append("Selected task: none")

    lines.append(f"Policy: {outcome.policy_status}")
    lines.append(f"Drift signals: {outcome.drift_signals}")
    lines.append(f"Changed files: {len(outcome.changed_files)}")
    lines.append(f"Diff violations: {outcome.diff_violations}")

    if outcome.diff_details:
        for detail in outcome.diff_details:
            lines.append(f"  {detail}")

    if outcome.validation_passed is not None:
        status = "PASSED" if outcome.validation_passed else "FAILED"
        lines.append(f"Validation: {status}")
        lines.append(f"Command: {outcome.validation_command}")
    elif outcome.validation_command:
        lines.append(f"Validation: {outcome.validation_command}")

    if outcome.blocked:
        lines.append(f"BLOCKED: {outcome.block_reason}")
    elif outcome.selected_task is None:
        lines.append("Status: idle — no TODO tasks remaining")
    elif outcome.validation_passed is True:
        lines.append("Status: ready to commit")
    elif outcome.validation_passed is False:
        lines.append("Status: validation failed — do not commit")
    else:
        lines.append("Status: run complete")

    return "\n".join(lines)


def save_run_outcome(outcome: RunOutcome, root: Path = Path(".")) -> Path:
    """Persist a run outcome to .forge/runs/ as a Markdown file."""
    runs_dir = root / _SUMMARY_DIR
    runs_dir.mkdir(parents=True, exist_ok=True)
    safe_ts = outcome.timestamp.replace(":", "-").replace("+", "p").replace("T", "_")
    filename = f"run-{safe_ts}.md"
    path = runs_dir / filename

    lines = [
        "# Forge Run Summary",
        "",
        f"Timestamp: {outcome.timestamp}",
    ]

    if outcome.selected_task:
        lines.append(f"Task: {outcome.selected_task.task_id} — {outcome.selected_task.title}")
    else:
        lines.append("Task: none")

    lines.append(f"Policy: {outcome.policy_status}")
    lines.append(f"Drift signals: {outcome.drift_signals}")
    lines.append(f"Changed files: {len(outcome.changed_files)}")

    if outcome.changed_files:
        lines.append("")
        for f in outcome.changed_files:
            lines.append(f"- {f}")

    lines.append(f"\nDiff violations: {outcome.diff_violations}")
    if outcome.diff_details:
        for detail in outcome.diff_details:
            lines.append(f"- {detail}")

    if outcome.validation_passed is not None:
        status = "PASSED" if outcome.validation_passed else "FAILED"
        lines.append(f"\nValidation: {status}")
        lines.append(f"Command: {outcome.validation_command}")
        if outcome.validation_output:
            lines.append(f"\n```\n{outcome.validation_output}\n```")

    if outcome.blocked:
        lines.append(f"\nBLOCKED: {outcome.block_reason}")

    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
