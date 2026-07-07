"""Build read-only dry-run reports for Autonomous Forge repositories."""

from __future__ import annotations

from pathlib import Path

from autonomous_forge.plan import PlanTask, parse_plan_tasks, select_eligible_task
from autonomous_forge.policy import PolicyParseError, parse_repository_policy


def _format_task(task: PlanTask | None) -> str:
    if task is None:
        return "none"
    return f"{task.task_id} [{task.priority}/{task.status}] {task.title}"


def _policy_status(policy_text: str | None) -> str:
    if policy_text is None:
        return "missing"

    try:
        parse_repository_policy(policy_text)
    except PolicyParseError as exc:
        return f"malformed: {exc}"

    return "present and readable"


def build_repository_report(
    plan_text: str,
    state_text: str | None = None,
    policy_text: str | None = None,
) -> str:
    """Return a concise dry-run repository report without changing files."""
    tasks = parse_plan_tasks(plan_text)
    selected_task = select_eligible_task(tasks)
    todo_count = sum(1 for task in tasks if task.status == "TODO")
    done_count = sum(1 for task in tasks if task.status == "DONE")
    blocked_count = sum(1 for task in tasks if task.status == "BLOCKED")
    skipped_count = sum(1 for task in tasks if task.status == "SKIPPED")
    state_status = "present" if state_text is not None else "missing"

    return "\n".join(
        [
            "Autonomous Forge dry-run report",
            "Mode: read-only",
            f"Plan tasks: {len(tasks)}",
            f"TODO tasks: {todo_count}",
            f"DONE tasks: {done_count}",
            f"BLOCKED tasks: {blocked_count}",
            f"SKIPPED tasks: {skipped_count}",
            f"Next eligible task: {_format_task(selected_task)}",
            f"State file: {state_status}",
            f"Policy file: {_policy_status(policy_text)}",
            "Suggested validation: PYTHONPATH=src python -m pytest",
        ]
    )


def read_repository_report(
    plan_path: Path = Path(".ai/AUTONOMOUS_PLAN.md"),
    state_path: Path = Path(".ai/AUTONOMOUS_STATE.md"),
    policy_path: Path = Path(".forge/policy.md"),
) -> str:
    """Read local repository files and build a dry-run report."""
    plan_text = plan_path.read_text(encoding="utf-8")
    state_text = state_path.read_text(encoding="utf-8") if state_path.exists() else None
    policy_text = policy_path.read_text(encoding="utf-8") if policy_path.exists() else None
    return build_repository_report(plan_text, state_text, policy_text)
