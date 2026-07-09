"""Mark task status in the autonomous plan file."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from autonomous_forge.plan import _SUPPORTED_STATUSES, _TASK_HEADING_RE


@dataclass(frozen=True)
class MarkResult:
    """Result of a task status update."""

    task_id: str
    old_status: str
    new_status: str
    updated: bool
    reason: str


def mark_task_status(
    task_id: str,
    new_status: str,
    plan_path: Path | None = None,
) -> MarkResult:
    """Update a task's status in the plan file. Returns the result."""
    if new_status not in _SUPPORTED_STATUSES:
        return MarkResult(
            task_id=task_id,
            old_status="",
            new_status=new_status,
            updated=False,
            reason=f"Unsupported status: {new_status}. Must be one of: {', '.join(sorted(_SUPPORTED_STATUSES))}",
        )

    path = plan_path or Path(".ai/AUTONOMOUS_PLAN.md")
    if not path.exists():
        return MarkResult(
            task_id=task_id,
            old_status="",
            new_status=new_status,
            updated=False,
            reason=f"Plan file not found: {path}",
        )

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    in_target = False
    old_status = ""
    status_line_idx = None

    for i, line in enumerate(lines):
        heading = _TASK_HEADING_RE.match(line.rstrip("\n\r"))
        if heading:
            if heading.group(1) == task_id:
                in_target = True
                continue
            elif in_target:
                break
        if in_target:
            m = re.match(r"^Status:\s*(.+)$", line.rstrip("\n\r"))
            if m:
                old_status = m.group(1).strip()
                status_line_idx = i
                break

    if status_line_idx is None:
        return MarkResult(
            task_id=task_id,
            old_status="",
            new_status=new_status,
            updated=False,
            reason=f"Task {task_id} not found in {path}",
        )

    if old_status == new_status:
        return MarkResult(
            task_id=task_id,
            old_status=old_status,
            new_status=new_status,
            updated=False,
            reason=f"Already {new_status}",
        )

    ending = "\n" if not lines[status_line_idx].endswith("\r\n") else "\r\n"
    lines[status_line_idx] = f"Status: {new_status}{ending}"
    path.write_text("".join(lines), encoding="utf-8")

    return MarkResult(
        task_id=task_id,
        old_status=old_status,
        new_status=new_status,
        updated=True,
        reason=f"{old_status} -> {new_status}",
    )


def format_mark_result(result: MarkResult) -> str:
    """Format a mark result as a human-readable string."""
    if result.updated:
        return f"{result.task_id}: {result.reason}"
    return f"{result.task_id}: {result.reason}"
