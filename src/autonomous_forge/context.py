"""Generate a comprehensive project context briefing from forge metadata."""

from __future__ import annotations

from pathlib import Path

from autonomous_forge.drift import collect_drift_signals
from autonomous_forge.inventory import collect_inventory_signals
from autonomous_forge.plan import PlanTask, parse_plan_tasks, select_eligible_task
from autonomous_forge.policy import PolicyParseError, parse_repository_policy


def _safe_read(path: Path) -> str | None:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def _format_task(task: PlanTask) -> str:
    return f"{task.task_id} [{task.priority}/{task.status}] {task.title}"


def _task_summary(tasks: list[PlanTask]) -> list[str]:
    todo = [t for t in tasks if t.status == "TODO"]
    done = [t for t in tasks if t.status == "DONE"]
    blocked = [t for t in tasks if t.status == "BLOCKED"]
    lines = [f"Tasks: {len(tasks)} total, {len(done)} done, {len(todo)} todo, {len(blocked)} blocked"]
    if todo:
        lines.append("Open work:")
        for t in todo:
            lines.append(f"  {_format_task(t)}")
    return lines


def _policy_summary(policy_text: str | None) -> list[str]:
    if policy_text is None:
        return ["Policy: not found"]
    try:
        policy = parse_repository_policy(policy_text)
    except PolicyParseError as exc:
        return [f"Policy: malformed — {exc}"]
    return [
        f"Policy: {len(policy.allowed_paths)} allowed paths, "
        f"{len(policy.prohibited_paths)} prohibited, "
        f"{len(policy.approval_required)} need approval",
    ]


def _drift_summary(
    plan_text: str,
    state_text: str | None,
    changelog_text: str | None,
    policy_text: str | None,
    root: Path,
) -> list[str]:
    signals = collect_drift_signals(
        plan_text, state_text, changelog_text, policy_text, root
    )
    if not signals:
        return ["Drift: none detected"]
    lines = [f"Drift: {len(signals)} signal(s)"]
    for s in signals:
        lines.append(f"  [{s.severity}] {s.message}")
    return lines


def _inventory_summary(root: Path) -> list[str]:
    signals = collect_inventory_signals(root)
    missing = [s for s in signals if not s.present]
    if not missing:
        return ["Health: all expected files present"]
    lines = [f"Health: {len(missing)} expected file(s) missing"]
    for s in missing:
        lines.append(f"  missing: {s.path}")
    return lines


def _state_summary(state_text: str | None) -> list[str]:
    if state_text is None:
        return ["State: not found"]
    lines = []
    for raw_line in state_text.splitlines():
        line = raw_line.strip()
        if line.startswith("- Current task ID:"):
            lines.append(f"Current task: {line.split(':', 1)[1].strip()}")
        elif line.startswith("- Current task status:"):
            lines.append(f"Task status: {line.split(':', 1)[1].strip()}")
        elif line.startswith("- Current blockers:"):
            val = line.split(":", 1)[1].strip()
            if val.lower() not in ("none", "none."):
                lines.append(f"Blockers: {val}")
    return lines if lines else ["State: present but no active task"]


def build_project_context(
    root: Path = Path("."),
    plan_path: Path | None = None,
    state_path: Path | None = None,
    changelog_path: Path | None = None,
    policy_path: Path | None = None,
) -> str:
    """Generate a comprehensive project context briefing."""
    plan_p = plan_path or (root / ".ai/AUTONOMOUS_PLAN.md")
    state_p = state_path or (root / ".ai/AUTONOMOUS_STATE.md")
    changelog_p = changelog_path or (root / ".ai/AUTONOMOUS_CHANGELOG.md")
    policy_p = policy_path or (root / ".forge/policy.md")

    plan_text = _safe_read(plan_p)
    state_text = _safe_read(state_p)
    changelog_text = _safe_read(changelog_p)
    policy_text = _safe_read(policy_p)

    project_name = root.resolve().name

    lines = [
        f"Project context: {project_name}",
        "Mode: read-only",
        "",
    ]

    if plan_text is None:
        lines.append("Plan: not found — this repo may not use Autonomous Forge metadata.")
        lines.append("")
        lines.extend(_inventory_summary(root))
        return "\n".join(lines)

    tasks = parse_plan_tasks(plan_text)
    next_task = select_eligible_task(tasks)

    lines.extend(_task_summary(tasks))
    if next_task:
        lines.append(f"Next task: {_format_task(next_task)}")
    lines.append("")

    lines.extend(_state_summary(state_text))
    lines.append("")

    lines.extend(_policy_summary(policy_text))
    lines.append("")

    lines.extend(_drift_summary(plan_text, state_text, changelog_text, policy_text, root))
    lines.append("")

    lines.extend(_inventory_summary(root))

    return "\n".join(lines)
