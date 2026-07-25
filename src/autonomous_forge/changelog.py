"""Auto-append completed tasks to the changelog on commit.

Detects tasks whose Status just flipped to DONE (compared to the plan
file's content at HEAD) and appends one dated line per task to
`.ai/AUTONOMOUS_CHANGELOG.md`, so the changelog stops silently drifting
from the plan the way it did for AUTO-033 through AUTO-040 (no commit hash
is recorded — it isn't known until after the commit exists; the task ID is
searchable via `git log --grep`).
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from autonomous_forge.plan import PlanTask, parse_plan_tasks

CHANGELOG_RELATIVE_PATH = Path(".ai") / "AUTONOMOUS_CHANGELOG.md"


def _read_head_text(root: Path, relpath: str) -> str | None:
    """Read a file's content as of HEAD, or None if unavailable.

    Decodes explicitly as UTF-8 rather than relying on `text=True`'s
    locale-default decoding: on Windows that default is often cp1252,
    which silently mangles non-ASCII bytes (e.g. em-dashes) instead of
    raising — every task heading using " — " then fails to match and the
    file appears to have zero tasks. Every other subprocess git call in
    this project only reads paths/hashes/branch names (pure ASCII), so
    this is the first place file *content* is piped through subprocess
    text mode, and the first place this class of bug can surface.
    """
    try:
        result = subprocess.run(
            ["git", "show", f"HEAD:{relpath}"],
            capture_output=True, cwd=root, timeout=10,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8")


def find_newly_done_tasks(
    root: Path = Path("."),
    plan_path: Path | None = None,
) -> tuple[PlanTask, ...]:
    """Find tasks whose Status is DONE now but wasn't DONE at HEAD.

    Compares the current (working-tree) plan file against the version
    committed at HEAD. A task counts as newly done if it's DONE now and
    either didn't exist at HEAD or had a different status there. Returns
    an empty tuple if the plan is missing, unreadable, or unchanged.
    """
    plan_p = plan_path or (root / ".ai/AUTONOMOUS_PLAN.md")
    if not plan_p.exists():
        return ()

    current_text = plan_p.read_text(encoding="utf-8")
    try:
        current_tasks = {t.task_id: t for t in parse_plan_tasks(current_text)}
    except Exception:
        return ()

    try:
        plan_relpath = plan_p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        plan_relpath = plan_p.name

    head_text = _read_head_text(root, plan_relpath)
    head_statuses: dict[str, str] = {}
    if head_text is not None:
        try:
            head_statuses = {t.task_id: t.status for t in parse_plan_tasks(head_text)}
        except Exception:
            head_statuses = {}

    return tuple(
        task for task in current_tasks.values()
        if task.status == "DONE" and head_statuses.get(task.task_id) != "DONE"
    )


def append_changelog_entries(
    tasks: tuple[PlanTask, ...],
    root: Path = Path("."),
    changelog_path: Path | None = None,
    timestamp: str | None = None,
) -> Path | None:
    """Append one dated line per newly-done task to the changelog.

    Only appends — never rewrites or reorders existing content. Only
    touches an already-existing changelog file; it does not create one
    (matching `forge mark`'s modify-in-place-only approach). Returns the
    changelog path if a line was appended, else None.
    """
    if not tasks:
        return None

    changelog_p = changelog_path or (root / CHANGELOG_RELATIVE_PATH)
    if not changelog_p.exists():
        return None

    ts = timestamp or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    date = ts.split("T", 1)[0]

    existing = changelog_p.read_text(encoding="utf-8")
    new_lines = [f"- {date}: {task.task_id} — {task.title} (DONE)" for task in tasks]
    updated = existing.rstrip("\n") + "\n" + "\n".join(new_lines) + "\n"
    changelog_p.write_text(updated, encoding="utf-8")
    return changelog_p
