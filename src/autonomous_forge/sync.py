"""Sync AUTO-xxx tasks to Forgejo issues (one-way: plan -> Forgejo)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

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

_AUTO_TAG_RE = re.compile(r"^\[AUTO-\d+\]")
_ANY_AUTO_ID_RE = re.compile(r"AUTO-\d+")


@dataclass(frozen=True)
class OrphanIssue:
    """A Forgejo issue with no matching AUTO-### task in the current plan."""

    number: int
    title: str
    url: str


@dataclass(frozen=True)
class OrphanReport:
    """Result of a read-only orphan-issue scan."""

    orphans: tuple[OrphanIssue, ...]
    repo: str
    errors: tuple[str, ...] = ()


def _detect_forgejo_repo(root: Path) -> str | None:
    """Extract owner/repo from the git remote URL."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, cwd=root, timeout=10,
        )
        url = result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return None

    match = re.search(r"forgejo\.familytechlab\.com[/:](.+?)(?:\.git)?$", url)
    if match:
        return match.group(1)
    return None


def _load_token() -> str | None:
    """Load Forgejo token from environment or .secrets.env."""
    token = os.environ.get("FORGEJO_TOKEN")
    if token:
        return token

    secrets_path = Path.home() / ".claude" / ".secrets.env"
    if secrets_path.exists():
        for line in secrets_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("FORGEJO_TOKEN="):
                val = line.split("=", 1)[1].strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                return val
    return None


class ForgejoClient:
    """Minimal Forgejo API client using only stdlib."""

    def __init__(self, repo: str, token: str):
        self.base = f"https://forgejo.familytechlab.com/api/v1/repos/{repo}"
        self.token = token

    def _request(
        self, method: str, path: str, data: dict | None = None
    ) -> dict | list | None:
        url = f"{self.base}{path}"
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={
                "Authorization": f"token {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode() if exc.fp else ""
            raise RuntimeError(
                f"Forgejo API {method} {path} returned {exc.code}: {error_body}"
            ) from exc

    def list_issues(self, state: str = "all", limit: int = 50) -> list[dict]:
        page = 1
        all_issues: list[dict] = []
        while True:
            issues = self._request(
                "GET", f"/issues?state={state}&type=issues&limit={limit}&page={page}"
            )
            if not issues:
                break
            all_issues.extend(issues)
            if len(issues) < limit:
                break
            page += 1
        return all_issues

    def create_issue(self, title: str, body: str, labels: list[int] | None = None,
                     milestone: int | None = None) -> dict:
        data: dict = {"title": title, "body": body}
        if labels:
            data["labels"] = labels
        if milestone:
            data["milestone"] = milestone
        return self._request("POST", "/issues", data)

    def update_issue(self, number: int, **kwargs) -> dict:
        return self._request("PATCH", f"/issues/{number}", kwargs)

    def add_comment(self, number: int, body: str) -> dict:
        return self._request("POST", f"/issues/{number}/comments", {"body": body})

    def list_labels(self) -> list[dict]:
        return self._request("GET", "/labels?limit=50") or []

    def create_label(self, name: str, color: str) -> dict:
        return self._request("POST", "/labels", {"name": name, "color": color})

    def list_milestones(self, state: str = "all") -> list[dict]:
        return self._request("GET", f"/milestones?state={state}&limit=50") or []

    def create_milestone(self, title: str) -> dict:
        return self._request("POST", "/milestones", {"title": title})

    def replace_labels(self, issue_number: int, label_ids: list[int]) -> list[dict]:
        return self._request("PUT", f"/issues/{issue_number}/labels", {"labels": label_ids})


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
    """
    bracketed = f"[{task_id}]"
    unbracketed = f"{task_id}:"
    for issue in issues:
        title = issue["title"]
        if title.startswith(bracketed) or title.startswith(unbracketed):
            return issue
    return None


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
    """Detect which roadmap version a task belongs to."""
    lines = plan_text.splitlines()
    current_version = None
    for line in lines:
        if re.match(r"^##\s+Roadmap\s+v\d+", line):
            current_version = line.lstrip("#").strip()
        if re.match(rf"^###\s+{re.escape(task.task_id)}\s", line):
            return current_version
    return None


def find_orphan_issues(issues: list[dict], tasks: list[PlanTask]) -> list[dict]:
    """Return open issues with no AUTO-### reference matching a current plan task."""
    task_ids = {task.task_id for task in tasks}
    orphans = []
    for issue in issues:
        if issue.get("state") != "open":
            continue
        match = _ANY_AUTO_ID_RE.search(issue.get("title", ""))
        if not match or match.group(0) not in task_ids:
            orphans.append(issue)
    return orphans


def execute_orphan_report(
    root: Path = Path("."),
    plan_path: Path | None = None,
    repo_override: str | None = None,
    token_override: str | None = None,
) -> OrphanReport:
    """Read-only scan for open Forgejo issues with no matching plan task.

    Makes GET calls only — never creates, updates, or comments on issues.
    """
    plan_p = plan_path or (root / ".ai/AUTONOMOUS_PLAN.md")
    plan_text = plan_p.read_text(encoding="utf-8")
    tasks = parse_plan_tasks(plan_text)

    repo = repo_override or _detect_forgejo_repo(root)
    if not repo:
        return OrphanReport(
            orphans=(),
            repo="unknown",
            errors=("Could not detect Forgejo repo from git remote.",),
        )

    token = token_override or _load_token()
    if not token:
        return OrphanReport(
            orphans=(),
            repo=repo,
            errors=(
                "No Forgejo token found. Set FORGEJO_TOKEN in environment "
                "or ~/.claude/.secrets.env.",
            ),
        )

    client = ForgejoClient(repo, token)
    try:
        issues = client.list_issues(state="open")
    except RuntimeError as exc:
        return OrphanReport(orphans=(), repo=repo, errors=(str(exc),))

    orphans = tuple(
        OrphanIssue(number=i["number"], title=i["title"], url=i.get("html_url", ""))
        for i in find_orphan_issues(issues, tasks)
    )
    return OrphanReport(orphans=orphans, repo=repo)


def format_orphan_report(report: OrphanReport) -> str:
    """Format an orphan-issue report as a human-readable summary."""
    lines = ["Forge orphan-issue report", f"Repo: {report.repo}"]

    if report.errors:
        for err in report.errors:
            lines.append(f"ERROR: {err}")
        if not report.orphans:
            return "\n".join(lines)

    if not report.orphans:
        lines.append("No orphan issues.")
        return "\n".join(lines)

    lines.append(f"Orphan issues: {len(report.orphans)}")
    lines.append("")
    for orphan in report.orphans:
        lines.append(f"  #{orphan.number}: {orphan.title}")

    return "\n".join(lines)


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

    if dry_run:
        actions = []
        for task in tasks:
            actions.append(SyncAction(
                task_id=task.task_id,
                action="would-create" if task.status == "TODO" else "would-sync",
                detail=f"{task.title} [{task.priority}/{task.status}]",
            ))
        return SyncResult(actions=tuple(actions), repo=repo)

    client = ForgejoClient(repo, token)
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
