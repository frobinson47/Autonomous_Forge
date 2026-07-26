"""Record and check human approvals for policy-gated tasks.

A task whose plan entry sets ``Approval needed: <category>`` cannot be
committed until a matching record exists in ``.forge/approvals.md`` — see
DEC-013. This module only checks for a task ID's presence in that file; it
does not attempt to match the recorded category text against the plan's
``Approval needed`` text or the policy's ``Human approval required`` bullets,
since free-text-to-free-text matching would be fragile in both directions.
Approval is a deliberate human action (running `forge approve`), not an
automated inference.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

APPROVALS_RELATIVE_PATH = Path(".forge") / "approvals.md"
_APPROVAL_HEADING_RE = re.compile(r"^## (AUTO-\d{3,}) — (.+)$")
_HEADER = "# Human Approvals\n"


@dataclass(frozen=True)
class ApprovalRecord:
    """A single recorded human approval."""

    task_id: str
    category: str
    approved_at: str
    note: str


def _resolve_path(root: Path, approvals_path: Path | None) -> Path:
    return approvals_path or (root / APPROVALS_RELATIVE_PATH)


def parse_approvals(approvals_text: str) -> list[ApprovalRecord]:
    """Parse recorded approvals from ``.forge/approvals.md`` Markdown."""
    lines = approvals_text.splitlines()
    records: list[ApprovalRecord] = []
    index = 0

    while index < len(lines):
        heading_match = _APPROVAL_HEADING_RE.match(lines[index])
        if not heading_match:
            index += 1
            continue

        task_id, category = heading_match.groups()
        approved_at = ""
        note = ""
        index += 1

        while index < len(lines) and not lines[index].startswith("## "):
            line = lines[index]
            if line.startswith("Approved:"):
                approved_at = line[len("Approved:"):].strip()
            elif line.startswith("Note:"):
                note = line[len("Note:"):].strip()
            index += 1

        records.append(
            ApprovalRecord(
                task_id=task_id,
                category=category.strip(),
                approved_at=approved_at,
                note=note,
            )
        )

    return records


def has_approval(
    task_id: str,
    root: Path = Path("."),
    approvals_path: Path | None = None,
) -> bool:
    """Return True if any recorded approval exists for the given task ID."""
    path = _resolve_path(root, approvals_path)
    if not path.exists():
        return False
    records = parse_approvals(path.read_text(encoding="utf-8"))
    return any(r.task_id == task_id for r in records)


def record_approval(
    task_id: str,
    category: str,
    root: Path = Path("."),
    approvals_path: Path | None = None,
    note: str = "",
    timestamp: str | None = None,
) -> Path:
    """Append a new approval record, creating the file with its header if needed."""
    path = _resolve_path(root, approvals_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = timestamp or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    lines = [f"## {task_id} — {category}", f"Approved: {ts}"]
    if note:
        lines.append(f"Note: {note}")
    entry = "\n".join(lines) + "\n"

    if not path.exists():
        path.write_text(_HEADER + "\n" + entry, encoding="utf-8")
    else:
        existing = path.read_text(encoding="utf-8")
        separator = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
        path.write_text(existing + separator + entry, encoding="utf-8")

    return path


def format_approval_confirmation(task_id: str, category: str, path: Path) -> str:
    """Format a human-readable confirmation after recording an approval."""
    return f"Approved {task_id} — {category}\nRecorded in: {path}"
