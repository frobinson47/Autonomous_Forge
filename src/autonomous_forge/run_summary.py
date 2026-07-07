"""Build read-only local run-summary previews."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from autonomous_forge.plan import PlanTask, parse_plan_tasks, select_eligible_task
from autonomous_forge.policy import PolicyParseError, parse_repository_policy


DEFAULT_VALIDATION_PLAN = "PYTHONPATH=src python -m pytest"
DEFAULT_NOTES = "Read-only preview only; no run-summary file was written."


def _format_selected_task(task: PlanTask | None) -> str:
    if task is None:
        return "none"
    return f"{task.task_id} — {task.title}"


def _format_task_status(task: PlanTask | None) -> str:
    if task is None:
        return "unknown"
    return task.status


def _policy_status(policy_text: str | None) -> str:
    if policy_text is None:
        return "missing"

    try:
        parse_repository_policy(policy_text)
    except PolicyParseError as exc:
        return f"malformed: {exc}"

    return "present and readable"


def build_run_summary_preview(
    plan_text: str,
    policy_text: str | None = None,
    *,
    timestamp: str | None = None,
    validation_plan: str = DEFAULT_VALIDATION_PLAN,
    validation_result: str = "not run",
    changed_files_summary: str = "none",
    commit: str = "none",
    notes: str = DEFAULT_NOTES,
) -> str:
    """Return the documented run-summary shape without writing files."""
    tasks = parse_plan_tasks(plan_text)
    selected_task = select_eligible_task(tasks)
    run_timestamp = timestamp or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    return "\n".join(
        [
            f"Run timestamp: {run_timestamp}",
            f"Selected task: {_format_selected_task(selected_task)}",
            f"Task status before run: {_format_task_status(selected_task)}",
            f"Policy status: {_policy_status(policy_text)}",
            f"Validation plan: {validation_plan}",
            f"Validation result: {validation_result}",
            f"Changed files summary: {changed_files_summary}",
            f"Commit: {commit}",
            f"Notes: {notes}",
        ]
    )


def read_run_summary_preview(
    plan_path: Path = Path(".ai/AUTONOMOUS_PLAN.md"),
    policy_path: Path = Path(".forge/policy.md"),
    *,
    timestamp: str | None = None,
) -> str:
    """Read local files and build a run-summary preview without writing files."""
    plan_text = plan_path.read_text(encoding="utf-8")
    policy_text = policy_path.read_text(encoding="utf-8") if policy_path.exists() else None
    return build_run_summary_preview(plan_text, policy_text, timestamp=timestamp)
