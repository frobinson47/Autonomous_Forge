"""Quick at-a-glance forge status."""

from __future__ import annotations

import subprocess
from pathlib import Path

from autonomous_forge.plan import parse_plan_tasks, select_eligible_task


def get_status(
    root: Path = Path("."),
    plan_path: Path | None = None,
) -> str:
    """Return a compact one-screen status summary."""
    plan = plan_path or root / ".ai" / "AUTONOMOUS_PLAN.md"
    lines: list[str] = []

    branch = _git_branch(root)
    dirty = _git_dirty_count(root)
    lines.append(f"Branch: {branch}  Dirty: {dirty}")

    if plan.exists():
        text = plan.read_text(encoding="utf-8")
        tasks = parse_plan_tasks(text)
        todo = sum(1 for t in tasks if t.status == "TODO")
        done = sum(1 for t in tasks if t.status == "DONE")
        blocked = sum(1 for t in tasks if t.status == "BLOCKED")
        lines.append(f"Tasks: {len(tasks)} total, {todo} TODO, {done} DONE, {blocked} BLOCKED")
        nxt = select_eligible_task(tasks)
        if nxt:
            lines.append(f"Next: {nxt.task_id} [{nxt.priority}] {nxt.title}")
        else:
            lines.append("Next: none")
    else:
        lines.append("Plan: not found")

    last_run = _last_run_summary(root)
    if last_run:
        lines.append(f"Last run: {last_run}")

    policy = root / ".forge" / "policy.md"
    lines.append(f"Policy: {'present' if policy.exists() else 'missing'}")

    return "\n".join(lines)


def _git_branch(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "unknown"


def _git_dirty_count(root: Path) -> int:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "-u"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return -1
        return len([l for l in result.stdout.splitlines() if l.strip()])
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return -1


def _last_run_summary(root: Path) -> str:
    runs_dir = root / ".forge" / "runs"
    if not runs_dir.is_dir():
        return ""
    files = sorted(runs_dir.glob("run-*.md"), reverse=True)
    if not files:
        return ""
    name = files[0].stem
    timestamp = name.replace("run-", "")
    return timestamp
