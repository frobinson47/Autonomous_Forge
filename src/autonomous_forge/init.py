"""Scaffold Autonomous Forge metadata into a repository."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from autonomous_forge.config import DEFAULT_CONFIG_TEMPLATE


@dataclass(frozen=True)
class InitResult:
    """Summary of files created during initialization."""

    created: tuple[str, ...]
    skipped: tuple[str, ...]


_PLAN_TEMPLATE = """\
# Autonomous Forge Roadmap

## Product vision

{project_name} uses Autonomous Forge to keep a clear improvement plan, choose small tasks, check results, and record what happened.

## Product scope and non-goals

This roadmap tracks incremental improvements. It is not a replacement for project management, issue tracking, or deployment tooling.

## Current architecture

To be documented as the project evolves.

## Current implementation status

Roadmap v1 is in progress.

## Technical debt

None documented yet.

## Prioritized roadmap

## Roadmap v1

## Future Ideas

## Do Not Change Without Explicit Human Approval

- Remote and branch settings.
- Repository visibility and access controls.
- Production infrastructure.
- Features that run external commands.
- Credential handling, telemetry, analytics, billing, or deployment behavior.
"""

_STATE_TEMPLATE = """\
# Autonomous State

- Current roadmap version: v1
- Current task ID: none
- Current task status: none
- Current branch: main
- Last run timestamp: none
- Last successful commit hash: none
- Latest run summary: Initial scaffold.
- Files changed in the latest run: none.
- Validation commands and results: none.
- Current blockers: None.
- Known risks and assumptions: None.
- Recommended next task: Add the first task to the roadmap.
"""

_CHANGELOG_TEMPLATE = """\
# Autonomous Changelog

## {date} — Bootstrap

- Task ID: Bootstrap
- Summary: Initialized Autonomous Forge metadata for {project_name}.
- Validation completed: Scaffold only; no code changes.
- Commit hash: pending
- Follow-up notes: Add the first roadmap task.
"""

_DECISIONS_TEMPLATE = """\
# Decisions Log

Record non-obvious decisions here so future sessions understand why things are the way they are.
"""

_POLICY_TEMPLATE = """\
# {project_name} Policy

## Allowed paths

- src/**
- tests/**
- docs/**
- README.md
- .ai/**

## Prohibited paths

- .env
- .env.*
- **/*secret*
- **/*token*
- **/*.pem
- **/*.key

## Human approval required

- Adding network access or external service calls.
- Running external commands from product code.
- Changing repository visibility, licensing, or access controls.
- Adding telemetry, analytics, tracking, or personal-data collection.

## Validation expectations

- Run targeted tests for changed behavior.
- Record unavailable validation honestly in `.ai/AUTONOMOUS_STATE.md`.
"""

_GITIGNORE_ADDITION = "\n# Autonomous Forge session files\n.forge/sessions/\n.forge/.lock\n"


def _write_if_missing(path: Path, content: str) -> bool:
    """Write content to path if it doesn't exist. Return True if created."""
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def init_forge(
    root: Path = Path("."),
    project_name: str | None = None,
    date: str = "undated",
) -> InitResult:
    """Scaffold Autonomous Forge metadata files into a repository."""
    name = project_name or root.resolve().name
    created: list[str] = []
    skipped: list[str] = []

    files = [
        (".ai/AUTONOMOUS_PLAN.md", _PLAN_TEMPLATE.format(project_name=name)),
        (".ai/AUTONOMOUS_STATE.md", _STATE_TEMPLATE),
        (".ai/AUTONOMOUS_CHANGELOG.md", _CHANGELOG_TEMPLATE.format(project_name=name, date=date)),
        (".ai/DECISIONS.md", _DECISIONS_TEMPLATE),
        (".forge/policy.md", _POLICY_TEMPLATE.format(project_name=name)),
        (".forge/config.toml", DEFAULT_CONFIG_TEMPLATE),
    ]

    for rel_path, content in files:
        if _write_if_missing(root / rel_path, content):
            created.append(rel_path)
        else:
            skipped.append(rel_path)

    gitignore_path = root / ".gitignore"
    if gitignore_path.exists():
        existing = gitignore_path.read_text(encoding="utf-8")
        if ".forge/sessions/" not in existing:
            gitignore_path.write_text(existing + _GITIGNORE_ADDITION, encoding="utf-8")
            created.append(".gitignore (appended)")
        else:
            skipped.append(".gitignore (already has sessions ignore)")
    else:
        gitignore_path.write_text(_GITIGNORE_ADDITION.lstrip(), encoding="utf-8")
        created.append(".gitignore")

    return InitResult(created=tuple(created), skipped=tuple(skipped))


def format_init_result(result: InitResult) -> str:
    """Format an init result as a human-readable summary."""
    lines = ["Forge initialized"]
    if result.created:
        lines.append(f"Created {len(result.created)} file(s):")
        for f in result.created:
            lines.append(f"  {f}")
    if result.skipped:
        lines.append(f"Skipped {len(result.skipped)} file(s) (already exist):")
        for f in result.skipped:
            lines.append(f"  {f}")
    if not result.created:
        lines.append("All forge metadata already exists.")
    return "\n".join(lines)
