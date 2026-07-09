"""Export forge state as JSON for programmatic consumption."""

from __future__ import annotations

import json
from pathlib import Path

from autonomous_forge.log import list_runs
from autonomous_forge.plan import parse_plan_tasks, select_eligible_task


def export_state(
    root: Path = Path("."),
    plan_path: Path | None = None,
    include_runs: bool = False,
    run_limit: int = 20,
) -> str:
    """Export current forge state as a JSON string."""
    plan = plan_path or root / ".ai" / "AUTONOMOUS_PLAN.md"

    data: dict = {
        "version": "1",
        "plan": {"found": False, "tasks": [], "counts": {}},
        "policy": {"found": False},
        "next_task": None,
    }

    if plan.exists():
        text = plan.read_text(encoding="utf-8")
        tasks = parse_plan_tasks(text)
        nxt = select_eligible_task(tasks)

        data["plan"]["found"] = True
        data["plan"]["tasks"] = [
            {
                "id": t.task_id,
                "title": t.title,
                "priority": t.priority,
                "status": t.status,
            }
            for t in tasks
        ]
        data["plan"]["counts"] = {
            "total": len(tasks),
            "todo": sum(1 for t in tasks if t.status == "TODO"),
            "done": sum(1 for t in tasks if t.status == "DONE"),
            "blocked": sum(1 for t in tasks if t.status == "BLOCKED"),
            "skipped": sum(1 for t in tasks if t.status == "SKIPPED"),
        }
        if nxt:
            data["next_task"] = {
                "id": nxt.task_id,
                "title": nxt.title,
                "priority": nxt.priority,
            }

    policy = root / ".forge" / "policy.md"
    data["policy"]["found"] = policy.exists()

    if include_runs:
        entries = list_runs(root, limit=run_limit)
        data["runs"] = [
            {
                "timestamp": e.timestamp,
                "task": e.task,
                "validation": e.validation,
                "blocked": e.blocked,
                "changed_files": e.changed_files,
                "violations": e.diff_violations,
                "drift": e.drift_signals,
            }
            for e in entries
        ]

    return json.dumps(data, indent=2)
