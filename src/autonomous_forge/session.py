"""Capture and replay coding session context for handoff across interruptions."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


_SESSIONS_DIR = ".forge/sessions"


@dataclass(frozen=True)
class GitSnapshot:
    """Read-only snapshot of git state at pause time."""

    branch: str
    dirty_files: tuple[str, ...]
    recent_commits: tuple[str, ...]
    stash_list: tuple[str, ...]


@dataclass(frozen=True)
class SessionContext:
    """Full session context captured at pause time."""

    timestamp: str
    git: GitSnapshot
    working_on: str
    tried: str
    stuck_on: str
    half_finished: str
    next_steps: str
    notes: str


def _run_git(args: list[str], cwd: Path) -> str:
    """Run a git command and return stdout, or empty string on failure."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def capture_git_snapshot(root: Path = Path(".")) -> GitSnapshot:
    """Capture current git state without changing the repository."""
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], root) or "unknown"

    status_output = _run_git(["status", "--porcelain", "-u"], root)
    dirty_files = tuple(
        line[3:] for line in status_output.splitlines() if line.strip()
    ) if status_output else ()

    log_output = _run_git(
        ["log", "--oneline", "-10", "--no-decorate"], root
    )
    recent_commits = tuple(log_output.splitlines()) if log_output else ()

    stash_output = _run_git(["stash", "list"], root)
    stash_list = tuple(stash_output.splitlines()) if stash_output else ()

    return GitSnapshot(
        branch=branch,
        dirty_files=dirty_files,
        recent_commits=recent_commits,
        stash_list=stash_list,
    )


def build_session_snapshot(
    git: GitSnapshot,
    *,
    working_on: str = "",
    tried: str = "",
    stuck_on: str = "",
    half_finished: str = "",
    next_steps: str = "",
    notes: str = "",
    timestamp: str | None = None,
) -> SessionContext:
    """Build a session context from a git snapshot and mental-state fields."""
    ts = timestamp or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    return SessionContext(
        timestamp=ts,
        git=git,
        working_on=working_on,
        tried=tried,
        stuck_on=stuck_on,
        half_finished=half_finished,
        next_steps=next_steps,
        notes=notes,
    )


def serialize_session(ctx: SessionContext) -> str:
    """Serialize a session context to a human-readable Markdown document."""
    lines = [
        "# Session Handoff",
        "",
        f"Paused: {ctx.timestamp}",
        "",
        "## Git State",
        "",
        f"Branch: {ctx.git.branch}",
    ]

    if ctx.git.dirty_files:
        lines.append("")
        lines.append("Dirty files:")
        for f in ctx.git.dirty_files:
            lines.append(f"- {f}")

    if ctx.git.recent_commits:
        lines.append("")
        lines.append("Recent commits:")
        for c in ctx.git.recent_commits:
            lines.append(f"- {c}")

    if ctx.git.stash_list:
        lines.append("")
        lines.append("Stash:")
        for s in ctx.git.stash_list:
            lines.append(f"- {s}")

    sections = [
        ("What I was working on", ctx.working_on),
        ("What I tried", ctx.tried),
        ("Where I got stuck", ctx.stuck_on),
        ("What's half-finished", ctx.half_finished),
        ("What to do next", ctx.next_steps),
        ("Notes", ctx.notes),
    ]

    for heading, body in sections:
        if body:
            lines.extend(["", f"## {heading}", "", body])

    lines.append("")
    return "\n".join(lines)


def deserialize_session(text: str) -> SessionContext:
    """Parse a session handoff Markdown document back into a SessionContext."""
    lines = text.splitlines()

    timestamp = ""
    branch = "unknown"
    dirty_files: list[str] = []
    recent_commits: list[str] = []
    stash_list: list[str] = []
    sections: dict[str, str] = {}

    current_section: str | None = None
    current_lines: list[str] = []
    git_subsection: str | None = None

    _section_map = {
        "What I was working on": "working_on",
        "What I tried": "tried",
        "Where I got stuck": "stuck_on",
        "What's half-finished": "half_finished",
        "What to do next": "next_steps",
        "Notes": "notes",
    }

    for line in lines:
        if line.startswith("Paused: "):
            timestamp = line[len("Paused: "):]
            continue

        if line.startswith("## "):
            if current_section and current_lines:
                sections[current_section] = "\n".join(current_lines).strip()
            heading = line[3:].strip()
            current_section = _section_map.get(heading)
            current_lines = []
            if heading == "Git State":
                git_subsection = "git"
                current_section = None
            else:
                git_subsection = None
            continue

        if git_subsection == "git":
            if line.startswith("Branch: "):
                branch = line[len("Branch: "):]
            elif line == "Dirty files:":
                git_subsection = "dirty"
            elif line == "Recent commits:":
                git_subsection = "commits"
            elif line == "Stash:":
                git_subsection = "stash"
            continue

        if git_subsection == "dirty":
            if line.startswith("- "):
                dirty_files.append(line[2:])
            elif line.startswith("Recent commits:"):
                git_subsection = "commits"
            elif line.startswith("Stash:"):
                git_subsection = "stash"
            elif line.startswith("## "):
                git_subsection = None
            elif line.strip() == "":
                continue
            else:
                git_subsection = None
            continue

        if git_subsection == "commits":
            if line.startswith("- "):
                recent_commits.append(line[2:])
            elif line.startswith("Stash:"):
                git_subsection = "stash"
            elif line.startswith("## "):
                git_subsection = None
            elif line.strip() == "":
                continue
            else:
                git_subsection = None
            continue

        if git_subsection == "stash":
            if line.startswith("- "):
                stash_list.append(line[2:])
            elif line.startswith("## "):
                git_subsection = None
            elif line.strip() == "":
                continue
            else:
                git_subsection = None
            continue

        if current_section is not None:
            current_lines.append(line)

    if current_section and current_lines:
        sections[current_section] = "\n".join(current_lines).strip()

    return SessionContext(
        timestamp=timestamp,
        git=GitSnapshot(
            branch=branch,
            dirty_files=tuple(dirty_files),
            recent_commits=tuple(recent_commits),
            stash_list=tuple(stash_list),
        ),
        working_on=sections.get("working_on", ""),
        tried=sections.get("tried", ""),
        stuck_on=sections.get("stuck_on", ""),
        half_finished=sections.get("half_finished", ""),
        next_steps=sections.get("next_steps", ""),
        notes=sections.get("notes", ""),
    )


def save_session(ctx: SessionContext, root: Path = Path(".")) -> Path:
    """Write a session file to .forge/sessions/ and return the path."""
    sessions_dir = root / _SESSIONS_DIR
    sessions_dir.mkdir(parents=True, exist_ok=True)
    safe_ts = ctx.timestamp.replace(":", "-").replace("+", "p").replace("T", "_")
    filename = f"session-{safe_ts}.md"
    path = sessions_dir / filename
    path.write_text(serialize_session(ctx), encoding="utf-8")
    return path


def load_latest_session(root: Path = Path(".")) -> SessionContext | None:
    """Load the most recent session file, or None if no sessions exist."""
    sessions_dir = root / _SESSIONS_DIR
    if not sessions_dir.exists():
        return None
    files = sorted(sessions_dir.glob("session-*.md"))
    if not files:
        return None
    return deserialize_session(files[-1].read_text(encoding="utf-8"))


@dataclass(frozen=True)
class RootSession:
    """The most recent session context found for one repo root, if any."""

    root: Path
    context: SessionContext | None


def load_sessions_for_roots(roots: list[Path]) -> list[RootSession]:
    """Load the latest session context for each of several repo roots."""
    return [RootSession(root=root, context=load_latest_session(root)) for root in roots]


def format_multi_resume_briefing(sessions: list[RootSession]) -> str:
    """Format a combined resume briefing across several repo roots."""
    lines = [
        "Cross-repo session resume briefing",
        f"Repos: {len(sessions)}",
    ]

    for entry in sessions:
        lines.append("")
        lines.append(f"## {entry.root}")

        if entry.context is None:
            lines.append("No session found.")
            continue

        ctx = entry.context
        lines.append(f"Last paused: {ctx.timestamp}")
        lines.append(f"Branch: {ctx.git.branch}")
        if ctx.git.dirty_files:
            lines.append(f"Dirty files: {len(ctx.git.dirty_files)}")
        if ctx.working_on:
            lines.append(f"Working on: {ctx.working_on}")
        if ctx.next_steps:
            lines.append(f"Next steps: {ctx.next_steps}")

    return "\n".join(lines)


def format_resume_briefing(ctx: SessionContext) -> str:
    """Format a session context as a structured resume briefing."""
    lines = [
        "Session resume briefing",
        f"Last paused: {ctx.timestamp}",
        f"Branch: {ctx.git.branch}",
    ]

    if ctx.git.dirty_files:
        lines.append(f"Dirty files: {len(ctx.git.dirty_files)}")
        for f in ctx.git.dirty_files:
            lines.append(f"  {f}")

    if ctx.git.stash_list:
        lines.append(f"Stashed: {len(ctx.git.stash_list)}")

    briefing_sections = [
        ("Working on", ctx.working_on),
        ("Tried", ctx.tried),
        ("Stuck on", ctx.stuck_on),
        ("Half-finished", ctx.half_finished),
        ("Next steps", ctx.next_steps),
        ("Notes", ctx.notes),
    ]

    for label, body in briefing_sections:
        if body:
            lines.append(f"{label}: {body}")

    if ctx.git.recent_commits:
        lines.append("Recent commits:")
        for c in ctx.git.recent_commits[:5]:
            lines.append(f"  {c}")

    return "\n".join(lines)
