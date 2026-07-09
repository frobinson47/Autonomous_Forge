"""Add new tasks to the autonomous plan file."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from autonomous_forge.plan import (
    _PRIORITY_ORDER,
    _TASK_HEADING_RE,
    parse_plan_tasks,
)


@dataclass(frozen=True)
class AddResult:
    """Result of adding a task to the plan."""

    task_id: str
    title: str
    priority: str
    added: bool
    reason: str


def _next_task_id(plan_text: str) -> str:
    """Determine the next AUTO-xxx ID from existing tasks."""
    ids = [int(m.group(1)) for m in re.finditer(r"AUTO-(\d{3})", plan_text)]
    next_num = max(ids) + 1 if ids else 1
    return f"AUTO-{next_num:03d}"


def _find_insert_position(lines: list[str]) -> int:
    """Find the line index where a new task should be inserted.

    Inserts before '## Future Ideas' if it exists, otherwise at end of file.
    """
    for i, line in enumerate(lines):
        if line.strip().startswith("## Future Ideas"):
            # Insert before the heading, with a blank line
            return i
        if line.strip().startswith("## Do Not Change"):
            return i
    return len(lines)


def add_task(
    title: str,
    goal: str,
    priority: str = "P1",
    plan_path: Path | None = None,
    scope: str = "",
    files: str = "",
    acceptance: str = "",
    notes: str = "",
) -> AddResult:
    """Add a new task block to the plan file."""
    if priority not in _PRIORITY_ORDER:
        return AddResult(
            task_id="",
            title=title,
            priority=priority,
            added=False,
            reason=f"Unsupported priority: {priority}. Must be one of: {', '.join(sorted(_PRIORITY_ORDER))}",
        )

    path = plan_path or Path(".ai/AUTONOMOUS_PLAN.md")
    if not path.exists():
        return AddResult(
            task_id="",
            title=title,
            priority=priority,
            added=False,
            reason=f"Plan file not found: {path}",
        )

    text = path.read_text(encoding="utf-8")
    task_id = _next_task_id(text)

    block = _build_task_block(
        task_id=task_id,
        title=title,
        priority=priority,
        goal=goal,
        scope=scope or "TBD",
        files=files or "TBD",
        acceptance=acceptance or "TBD",
        notes=notes or "None.",
    )

    lines = text.splitlines(keepends=True)
    insert_at = _find_insert_position(
        [l.rstrip("\n\r") for l in lines]
    )

    # Ensure blank line before the new block
    block_lines = block.splitlines(keepends=True)
    if insert_at > 0 and lines[insert_at - 1].strip():
        block_lines.insert(0, "\n")

    lines[insert_at:insert_at] = block_lines

    path.write_text("".join(lines), encoding="utf-8")

    return AddResult(
        task_id=task_id,
        title=title,
        priority=priority,
        added=True,
        reason=f"Added to plan at {path}",
    )


def _build_task_block(
    task_id: str,
    title: str,
    priority: str,
    goal: str,
    scope: str,
    files: str,
    acceptance: str,
    notes: str,
) -> str:
    """Build a properly formatted task block."""
    return (
        f"### {task_id} — {title}\n"
        f"Priority: {priority}\n"
        f"Status: TODO\n"
        f"\n"
        f"Goal: {goal}\n"
        f"Why it matters: TBD\n"
        f"Scope: {scope}\n"
        f"Expected files or areas: {files}\n"
        f"Acceptance criteria: {acceptance}\n"
        f"Validation: TBD\n"
        f"Risks or assumptions: None.\n"
        f"Notes: {notes}\n"
        f"\n"
    )


def format_add_result(result: AddResult) -> str:
    """Format an add result as a human-readable string."""
    if result.added:
        return f"Added {result.task_id} [{result.priority}/TODO] {result.title}"
    return f"Not added: {result.reason}"
