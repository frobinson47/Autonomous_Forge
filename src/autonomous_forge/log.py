"""Read and summarize run history from .forge/runs/."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunEntry:
    """One parsed run from a run summary file."""

    path: Path
    timestamp: str
    task: str
    policy: str
    drift_signals: int
    changed_files: int
    diff_violations: int
    validation: str
    blocked: str
    commit_hash: str


_FIELD_RE = re.compile(r"^([A-Za-z ]+):\s*(.+)$")


def _parse_run_file(path: Path) -> RunEntry | None:
    """Parse a run summary Markdown file into a RunEntry."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    fields: dict[str, str] = {}
    for line in text.splitlines():
        m = _FIELD_RE.match(line.strip())
        if m:
            fields[m.group(1).strip().lower()] = m.group(2).strip()

    timestamp = fields.get("timestamp", "")
    if not timestamp:
        return None

    drift_str = fields.get("drift signals", "0")
    changed_str = fields.get("changed files", "0")
    violations_str = fields.get("diff violations", "0")

    try:
        drift = int(drift_str)
    except ValueError:
        drift = 0
    try:
        changed = int(changed_str)
    except ValueError:
        changed = 0
    try:
        violations = int(violations_str)
    except ValueError:
        violations = 0

    return RunEntry(
        path=path,
        timestamp=timestamp,
        task=fields.get("task", "none"),
        policy=fields.get("policy", "unknown"),
        drift_signals=drift,
        changed_files=changed,
        diff_violations=violations,
        validation=fields.get("validation", ""),
        blocked=fields.get("blocked", ""),
        commit_hash=fields.get("commit", ""),
    )


def list_runs(root: Path = Path("."), limit: int = 20) -> list[RunEntry]:
    """List run entries from .forge/runs/, newest first."""
    runs_dir = root / ".forge" / "runs"
    if not runs_dir.is_dir():
        return []

    files = sorted(runs_dir.glob("run-*.md"), reverse=True)
    entries: list[RunEntry] = []
    for f in files[:limit]:
        entry = _parse_run_file(f)
        if entry:
            entries.append(entry)
    return entries


def format_run_log(entries: list[RunEntry], verbose: bool = False) -> str:
    """Format run entries as a human-readable log."""
    if not entries:
        return "No run history found in .forge/runs/"

    lines = [f"Forge run log ({len(entries)} runs)", ""]

    for entry in entries:
        status = ""
        if entry.blocked:
            status = f"BLOCKED: {entry.blocked}"
        elif entry.validation == "PASSED":
            status = "PASSED"
        elif entry.validation == "FAILED":
            status = "FAILED"
        else:
            status = entry.validation or "no validation"

        commit_suffix = f"  [{entry.commit_hash}]" if entry.commit_hash else ""
        line = f"  {entry.timestamp}  {entry.task:<40s}  {status}{commit_suffix}"
        lines.append(line)

        if verbose:
            lines.append(f"    Files: {entry.changed_files}  Drift: {entry.drift_signals}  Violations: {entry.diff_violations}")
            lines.append(f"    Policy: {entry.policy}")
            if entry.commit_hash:
                lines.append(f"    Commit: {entry.commit_hash}")
            lines.append("")

    return "\n".join(lines)
