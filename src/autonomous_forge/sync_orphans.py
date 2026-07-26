"""Read-only orphan-issue reporting and explicit, human-triggered import into the plan."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from autonomous_forge.forgejo_client import (
    ForgejoClient,
    _detect_forgejo_repo,
    _load_token,
)
from autonomous_forge.plan import PlanTask, parse_plan_tasks
from autonomous_forge.planadd import add_task

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


@dataclass(frozen=True)
class ImportedTask:
    """One AUTO-xxx task stub created from an orphan Forgejo issue."""

    task_id: str
    title: str
    source_issue_number: int


@dataclass(frozen=True)
class ImportResult:
    """Result of importing orphan Forgejo issues into the plan."""

    imported: tuple[ImportedTask, ...]
    already_imported: tuple[int, ...]  # issue numbers skipped as already imported
    repo: str
    errors: tuple[str, ...] = ()


def _issue_already_imported(issue_number: int, plan_text: str) -> bool:
    """Check whether an orphan issue was already imported as a task.

    Detected by an existing task's Notes field referencing the issue
    number in the format written by `execute_import_orphans` — this is
    what makes re-running --import-orphans idempotent.
    """
    return re.search(rf"Forgejo issue #{issue_number}\b", plan_text) is not None


def execute_import_orphans(
    root: Path = Path("."),
    plan_path: Path | None = None,
    repo_override: str | None = None,
    token_override: str | None = None,
) -> ImportResult:
    """Convert current orphan Forgejo issues into AUTO-xxx plan task stubs.

    Explicit, human-triggered (see DEC-010 in .ai/DECISIONS.md) — a
    deliberate, scoped partial reversal of AUTO-035's read-only-only
    orphan-issue stance. Reuses AUTO-035's orphan detection (GET calls
    only against Forgejo), then writes new task blocks directly to the
    plan file via `add_task`, one per orphan not already imported. The
    human still reviews and commits the resulting plan diff — nothing
    here commits, pushes, or syncs back to Forgejo. `--report-orphans`
    remains unchanged and read-only; this is a separate, opt-in flag.
    """
    plan_p = plan_path or (root / ".ai/AUTONOMOUS_PLAN.md")
    report = execute_orphan_report(
        root, plan_path=plan_p, repo_override=repo_override, token_override=token_override,
    )
    if report.errors:
        return ImportResult(
            imported=(), already_imported=(), repo=report.repo, errors=report.errors,
        )

    imported: list[ImportedTask] = []
    already_imported: list[int] = []
    for orphan in report.orphans:
        plan_text = plan_p.read_text(encoding="utf-8")
        if _issue_already_imported(orphan.number, plan_text):
            already_imported.append(orphan.number)
            continue

        result = add_task(
            title=orphan.title,
            goal=f"Imported from Forgejo issue #{orphan.number}: {orphan.title}",
            priority="P2",
            plan_path=plan_p,
            notes=f"Imported from Forgejo issue #{orphan.number} ({orphan.url}).",
        )
        if result.added:
            imported.append(ImportedTask(
                task_id=result.task_id, title=orphan.title, source_issue_number=orphan.number,
            ))

    return ImportResult(
        imported=tuple(imported), already_imported=tuple(already_imported), repo=report.repo,
    )


def format_import_result(result: ImportResult) -> str:
    """Format an orphan-import result as a human-readable summary."""
    lines = ["Forge orphan-issue import", f"Repo: {result.repo}"]

    if result.errors:
        for err in result.errors:
            lines.append(f"ERROR: {err}")
        if not result.imported and not result.already_imported:
            return "\n".join(lines)

    if not result.imported and not result.already_imported:
        lines.append("No orphan issues to import.")
        return "\n".join(lines)

    lines.append(f"Imported: {len(result.imported)}")
    for t in result.imported:
        lines.append(f"  {t.task_id}: imported from issue #{t.source_issue_number} — {t.title}")

    if result.already_imported:
        lines.append(f"Already imported (skipped): {len(result.already_imported)}")
        for n in result.already_imported:
            lines.append(f"  issue #{n}")

    return "\n".join(lines)
