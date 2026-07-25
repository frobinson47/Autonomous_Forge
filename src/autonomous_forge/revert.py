"""Undo a completed task's commit and flip its plan status back to TODO."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from autonomous_forge.log import list_runs
from autonomous_forge.mark import mark_task_status


@dataclass(frozen=True)
class RevertResult:
    """Result of reverting a completed task's commit."""

    task_id: str
    reverted: bool
    original_commit: str
    revert_commit_hash: str
    status_updated: bool
    message: str


def _find_commit_for_task(task_id: str, root: Path, limit: int = 1000) -> str | None:
    """Find the most recent recorded commit hash for a task from run history.

    Run entries are newest-first (see `list_runs`), so the first match is
    the task's latest recorded commit — the one worth reverting.
    """
    for entry in list_runs(root, limit=limit):
        if entry.task.startswith(task_id) and entry.commit_hash:
            return entry.commit_hash
    return None


def _run_git(args: list[str], root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args, capture_output=True, text=True, cwd=root, timeout=30,
    )


def execute_revert(
    task_id: str,
    root: Path = Path("."),
    plan_path: Path | None = None,
    commit_override: str | None = None,
) -> RevertResult:
    """Revert a task's recorded commit (via `git revert`) and flip its plan
    Status back to TODO.

    Looks up the commit from run history (`.forge/runs/`) unless
    `commit_override` is given. Does not touch Forgejo directly — a
    subsequent `forge sync` will reopen the issue naturally, since the
    plan is the source of truth. Does not auto-commit the Status change,
    matching `forge mark`'s existing behavior.
    """
    commit_hash = commit_override or _find_commit_for_task(task_id, root)
    if not commit_hash:
        return RevertResult(
            task_id=task_id, reverted=False, original_commit="", revert_commit_hash="",
            status_updated=False,
            message=f"No recorded commit found for {task_id} in run history. Use --commit to specify one.",
        )

    try:
        result = _run_git(["revert", "--no-edit", commit_hash], root)
    except subprocess.SubprocessError as exc:
        return RevertResult(
            task_id=task_id, reverted=False, original_commit=commit_hash, revert_commit_hash="",
            status_updated=False, message=f"git error: {exc}",
        )

    if result.returncode != 0:
        # Leave a clean working tree rather than a half-finished revert.
        _run_git(["revert", "--abort"], root)
        detail = result.stderr.strip() or result.stdout.strip()
        return RevertResult(
            task_id=task_id, reverted=False, original_commit=commit_hash, revert_commit_hash="",
            status_updated=False, message=f"git revert failed (aborted): {detail}",
        )

    revert_hash = _run_git(["rev-parse", "--short", "HEAD"], root).stdout.strip()

    mark_result = mark_task_status(
        task_id, "TODO", plan_path=plan_path or (root / ".ai/AUTONOMOUS_PLAN.md"),
    )

    message = f"Reverted {commit_hash} as {revert_hash}."
    if mark_result.updated:
        message += f" Status: {mark_result.reason}."
    else:
        message += f" Status unchanged ({mark_result.reason})."

    return RevertResult(
        task_id=task_id,
        reverted=True,
        original_commit=commit_hash,
        revert_commit_hash=revert_hash,
        status_updated=mark_result.updated,
        message=message,
    )


def format_revert_result(result: RevertResult) -> str:
    """Format a revert result as a human-readable summary."""
    lines = [f"Forge revert: {result.task_id}"]
    if result.original_commit:
        lines.append(f"Target commit: {result.original_commit}")
    lines.append(result.message)
    lines.append(f"Result: {'REVERTED' if result.reverted else 'FAILED'}")
    return "\n".join(lines)
