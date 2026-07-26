"""Sync AUTO-xxx tasks to Forgejo issues (one-way: plan -> Forgejo)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from autonomous_forge.forgejo_client import ForgejoClient, _detect_forgejo_repo, _load_token
from autonomous_forge.plan import PlanTask, parse_plan_tasks


@dataclass(frozen=True)
class SyncAction:
    """One action taken or planned during sync."""

    task_id: str
    action: str  # "created", "closed", "reopened", "up-to-date", "label-updated", "skipped"
    issue_number: int | None = None
    detail: str = ""


@dataclass(frozen=True)
class SyncResult:
    """Complete result of a sync operation."""

    actions: tuple[SyncAction, ...]
    repo: str
    errors: tuple[str, ...] = ()


_STATUS_LABEL_MAP = {
    "TODO": "status:todo",
    "DONE": "status:done",
    "BLOCKED": "status:blocked",
    "SKIPPED": "status:skipped",
}

_PRIORITY_LABEL_MAP = {
    "P0": "priority:critical",
    "P1": "priority:high",
    "P2": "priority:medium",
    "P3": "priority:low",
}


def _task_issue_title(task: PlanTask) -> str:
    return f"[{task.task_id}] {task.title}"


def _task_issue_body(task: PlanTask, plan_text: str) -> str:
    lines = [
        f"**Task ID:** {task.task_id}",
        f"**Priority:** {task.priority}",
        f"**Status:** {task.status}",
        "",
    ]
    block = _extract_task_block(task.task_id, plan_text)
    if block:
        lines.append("---")
        lines.append("")
        lines.append(block)
    lines.append("")
    lines.append("*Synced from `.ai/AUTONOMOUS_PLAN.md` by `forge sync`.*")
    return "\n".join(lines)


def _extract_task_block(task_id: str, plan_text: str) -> str | None:
    """Extract the full task block from the plan for the issue body."""
    lines = plan_text.splitlines()
    in_block = False
    block_lines: list[str] = []
    for line in lines:
        if re.match(rf"^###\s+{re.escape(task_id)}\s", line):
            in_block = True
            continue
        if in_block:
            if line.startswith("### ") or line.startswith("## "):
                break
            block_lines.append(line)
    if block_lines:
        text = "\n".join(block_lines).strip()
        return text if text else None
    return None


def _ensure_labels(client: ForgejoClient) -> dict[str, int]:
    """Ensure all sync labels exist and return name->id mapping."""
    existing = {lab["name"]: lab["id"] for lab in client.list_labels()}
    needed = {
        "status:todo": "#0075ca",
        "status:done": "#1a7f37",
        "status:blocked": "#d73a4a",
        "status:skipped": "#6e7681",
        "priority:critical": "#b60205",
        "priority:high": "#d93f0b",
        "priority:medium": "#fbca04",
        "priority:low": "#0e8a16",
        "forge-sync": "#5319e7",
    }
    for name, color in needed.items():
        if name not in existing:
            result = client.create_label(name, color)
            existing[name] = result["id"]
    return existing


def _ensure_milestone(client: ForgejoClient, title: str) -> int:
    """Ensure a milestone exists and return its ID."""
    for ms in client.list_milestones():
        if ms["title"] == title:
            return ms["id"]
    result = client.create_milestone(title)
    return result["id"]


def _find_issue_for_task(task_id: str, issues: list[dict]) -> dict | None:
    """Find the Forgejo issue corresponding to an AUTO task.

    Matches this tool's own ``[AUTO-xxx] Title`` format as well as the
    unbracketed ``AUTO-xxx: Title`` format some repos already used before
    forge-sync existed — otherwise re-running sync against a repo with
    pre-existing manually-filed issues creates a full duplicate set instead
    of updating the originals.

    If more than one issue matches (e.g. a leftover duplicate from before
    this matching was fixed), prefer the lowest issue number — the original,
    not whichever the API happened to list first.
    """
    bracketed = f"[{task_id}]"
    unbracketed = f"{task_id}:"
    matches = [
        issue for issue in issues
        if issue["title"].startswith(bracketed) or issue["title"].startswith(unbracketed)
    ]
    if not matches:
        return None
    return min(matches, key=lambda issue: issue["number"])


def _labels_for_task(task: PlanTask, label_map: dict[str, int]) -> list[int]:
    """Build the label ID list for a task."""
    ids = []
    status_label = _STATUS_LABEL_MAP.get(task.status)
    if status_label and status_label in label_map:
        ids.append(label_map[status_label])
    priority_label = _PRIORITY_LABEL_MAP.get(task.priority)
    if priority_label and priority_label in label_map:
        ids.append(label_map[priority_label])
    if "forge-sync" in label_map:
        ids.append(label_map["forge-sync"])
    return ids


def _detect_roadmap_version(task: PlanTask, plan_text: str) -> str | None:
    """Detect which roadmap version a task belongs to.

    Only tasks directly under a ``## Roadmap vN`` heading get that milestone.
    Any other top-level (``##``) section — e.g. ``## Backlog`` — resets the
    current version to None, so tasks under it are left without an
    auto-detected milestone instead of silently inheriting whichever
    ``Roadmap vN`` heading last appeared earlier in the file.
    """
    lines = plan_text.splitlines()
    current_version = None
    for line in lines:
        if re.match(r"^##\s+Roadmap\s+v\d+", line):
            current_version = line.lstrip("#").strip()
        elif re.match(r"^##\s+\S", line):
            current_version = None
        if re.match(rf"^###\s+{re.escape(task.task_id)}\s", line):
            return current_version
    return None


def execute_sync(
    root: Path = Path("."),
    plan_path: Path | None = None,
    dry_run: bool = False,
    repo_override: str | None = None,
    token_override: str | None = None,
) -> SyncResult:
    """Sync plan tasks to Forgejo issues."""
    plan_p = plan_path or (root / ".ai/AUTONOMOUS_PLAN.md")
    plan_text = plan_p.read_text(encoding="utf-8")
    tasks = parse_plan_tasks(plan_text)

    repo = repo_override or _detect_forgejo_repo(root)
    if not repo:
        return SyncResult(
            actions=(),
            repo="unknown",
            errors=("Could not detect Forgejo repo from git remote.",),
        )

    token = token_override or _load_token()
    if not token:
        return SyncResult(
            actions=(),
            repo=repo,
            errors=(
                "No Forgejo token found. Set FORGEJO_TOKEN in environment "
                "or ~/.claude/.secrets.env.",
            ),
        )

    client = ForgejoClient(repo, token)

    if dry_run:
        # Query real issue state so "would-create" vs "would-sync" reflects
        # what a live run would actually do — previously this branch never
        # looked at Forgejo at all and derived the label purely from
        # task.status, which is wrong whenever a matching issue already
        # exists (e.g. every TODO task always said "would-create" even if
        # its issue was sitting right there).
        try:
            existing_issues = client.list_issues(state="all")
        except RuntimeError as exc:
            return SyncResult(actions=(), repo=repo, errors=(str(exc),))

        actions = []
        for task in tasks:
            issue = _find_issue_for_task(task.task_id, existing_issues)
            actions.append(SyncAction(
                task_id=task.task_id,
                action="would-create" if issue is None else "would-sync",
                issue_number=issue["number"] if issue else None,
                detail=f"{task.title} [{task.priority}/{task.status}]",
            ))
        return SyncResult(actions=tuple(actions), repo=repo)
    errors: list[str] = []
    actions: list[SyncAction] = []

    try:
        label_map = _ensure_labels(client)
    except RuntimeError as exc:
        return SyncResult(actions=(), repo=repo, errors=(str(exc),))

    milestone_cache: dict[str, int] = {}
    try:
        existing_issues = client.list_issues(state="all")
    except RuntimeError as exc:
        return SyncResult(actions=(), repo=repo, errors=(str(exc),))

    for task in tasks:
        try:
            issue = _find_issue_for_task(task.task_id, existing_issues)
            target_labels = _labels_for_task(task, label_map)

            roadmap_version = _detect_roadmap_version(task, plan_text)
            milestone_id = None
            if roadmap_version:
                if roadmap_version not in milestone_cache:
                    milestone_cache[roadmap_version] = _ensure_milestone(
                        client, roadmap_version
                    )
                milestone_id = milestone_cache[roadmap_version]

            if issue is None:
                body = _task_issue_body(task, plan_text)
                create_kwargs: dict = {
                    "title": _task_issue_title(task),
                    "body": body,
                    "labels": target_labels,
                }
                if milestone_id:
                    create_kwargs["milestone"] = milestone_id
                result = client.create_issue(**create_kwargs)
                issue_num = result["number"]

                if task.status == "DONE":
                    client.update_issue(issue_num, state="closed")
                    client.add_comment(issue_num, f"Closed by `forge sync` — task status is DONE.")

                actions.append(SyncAction(
                    task_id=task.task_id,
                    action="created",
                    issue_number=issue_num,
                    detail=task.title,
                ))
            else:
                issue_num = issue["number"]
                issue_state = issue["state"]
                issue_label_ids = sorted([lab["id"] for lab in issue.get("labels", [])])
                target_label_ids = sorted(target_labels)

                needs_update = False
                updates: list[str] = []

                if task.status == "DONE" and issue_state == "open":
                    client.update_issue(issue_num, state="closed")
                    client.add_comment(
                        issue_num,
                        f"Closed by `forge sync` — task status changed to DONE.",
                    )
                    needs_update = True
                    updates.append("closed")
                elif task.status == "TODO" and issue_state == "closed":
                    client.update_issue(issue_num, state="open")
                    client.add_comment(
                        issue_num,
                        f"Reopened by `forge sync` — task status changed back to TODO.",
                    )
                    needs_update = True
                    updates.append("reopened")

                if issue_label_ids != target_label_ids:
                    client.replace_labels(issue_num, target_labels)
                    needs_update = True
                    updates.append("labels updated")

                issue_milestone = issue.get("milestone")
                issue_milestone_id = issue_milestone["id"] if issue_milestone else None
                if milestone_id and issue_milestone_id != milestone_id:
                    client.update_issue(issue_num, milestone=milestone_id)
                    needs_update = True
                    updates.append("milestone updated")

                if needs_update:
                    actions.append(SyncAction(
                        task_id=task.task_id,
                        action=", ".join(updates),
                        issue_number=issue_num,
                        detail=task.title,
                    ))
                else:
                    actions.append(SyncAction(
                        task_id=task.task_id,
                        action="up-to-date",
                        issue_number=issue_num,
                        detail=task.title,
                    ))
        except RuntimeError as exc:
            errors.append(f"{task.task_id}: {exc}")
            actions.append(SyncAction(
                task_id=task.task_id,
                action="error",
                detail=str(exc),
            ))

    return SyncResult(actions=tuple(actions), repo=repo, errors=tuple(errors))


def format_sync_result(result: SyncResult) -> str:
    """Format a sync result as a human-readable report."""
    lines = [
        "Forge sync report",
        f"Repo: {result.repo}",
    ]

    if result.errors:
        for err in result.errors:
            lines.append(f"ERROR: {err}")
        if not result.actions:
            return "\n".join(lines)

    created = sum(1 for a in result.actions if a.action == "created")
    updated = sum(1 for a in result.actions if a.action not in ("created", "up-to-date", "error", "would-create", "would-sync"))
    up_to_date = sum(1 for a in result.actions if a.action == "up-to-date")

    lines.append(f"Tasks synced: {len(result.actions)}")
    if created:
        lines.append(f"  Created: {created}")
    if updated:
        lines.append(f"  Updated: {updated}")
    if up_to_date:
        lines.append(f"  Up to date: {up_to_date}")

    lines.append("")
    for action in result.actions:
        issue_ref = f" (#{action.issue_number})" if action.issue_number else ""
        lines.append(f"  {action.task_id}: {action.action}{issue_ref} — {action.detail}")

    return "\n".join(lines)
