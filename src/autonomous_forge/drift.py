"""Detect consistency drift between Autonomous Forge metadata files and the repository."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from autonomous_forge.plan import PlanTask, parse_plan_tasks
from autonomous_forge.policy import PolicyParseError, parse_repository_policy


@dataclass(frozen=True)
class DriftSignal:
    """A single consistency finding between metadata and repository state."""

    category: str
    severity: str
    message: str


_STATE_FIELD_RE = re.compile(r"^- ([^:]+):\s*(.+)$")
_CHANGELOG_TASK_RE = re.compile(r"^## \d{4}-\d{2}-\d{2} — (AUTO-\d{3}|.+)$")


def _parse_state_fields(state_text: str) -> dict[str, str]:
    """Extract key-value fields from the state file bullet list."""
    fields: dict[str, str] = {}
    for line in state_text.splitlines():
        match = _STATE_FIELD_RE.match(line)
        if match:
            fields[match.group(1).strip()] = match.group(2).strip()
    return fields


def _parse_changelog_task_ids(changelog_text: str) -> list[str]:
    """Extract task IDs referenced in changelog section headings."""
    ids: list[str] = []
    for line in changelog_text.splitlines():
        match = _CHANGELOG_TASK_RE.match(line)
        if match:
            ids.append(match.group(1))
    return ids


def _check_state_vs_plan(
    state_fields: dict[str, str],
    tasks: list[PlanTask],
) -> list[DriftSignal]:
    """Check that the state file's current task matches the plan."""
    signals: list[DriftSignal] = []
    task_map = {t.task_id: t for t in tasks}

    current_task_raw = state_fields.get("Current task ID", "")
    current_task_id_match = re.match(r"(AUTO-\d{3})", current_task_raw)
    if not current_task_id_match:
        if current_task_raw:
            signals.append(DriftSignal(
                category="state-plan",
                severity="warn",
                message=f"State references unrecognized task format: {current_task_raw}",
            ))
        return signals

    current_task_id = current_task_id_match.group(1)
    if current_task_id not in task_map:
        signals.append(DriftSignal(
            category="state-plan",
            severity="error",
            message=f"State references {current_task_id} but it does not exist in the plan.",
        ))
        return signals

    plan_task = task_map[current_task_id]
    state_status = state_fields.get("Current task status", "")
    if state_status and state_status != plan_task.status:
        signals.append(DriftSignal(
            category="state-plan",
            severity="error",
            message=(
                f"State says {current_task_id} is {state_status} "
                f"but plan says {plan_task.status}."
            ),
        ))

    return signals


def _check_stale_state(state_fields: dict[str, str]) -> list[DriftSignal]:
    """Check for placeholder or unresolved values in the state file."""
    signals: list[DriftSignal] = []

    commit_hash = state_fields.get("Last successful commit hash", "")
    if commit_hash and "pending" in commit_hash.lower():
        signals.append(DriftSignal(
            category="stale-state",
            severity="warn",
            message=f"Commit hash is unresolved: {commit_hash}",
        ))

    return signals


def _check_changelog_vs_plan(
    changelog_task_ids: list[str],
    tasks: list[PlanTask],
) -> list[DriftSignal]:
    """Check that changelog entries reference tasks that exist in the plan."""
    signals: list[DriftSignal] = []
    plan_ids = {t.task_id for t in tasks}
    for cid in changelog_task_ids:
        if re.match(r"^AUTO-\d{3}$", cid) and cid not in plan_ids:
            signals.append(DriftSignal(
                category="changelog-plan",
                severity="warn",
                message=f"Changelog references {cid} which is not in the plan.",
            ))
    return signals


def _check_policy_path_existence(
    policy_text: str,
    root: Path,
) -> list[DriftSignal]:
    """Check that policy allowed/prohibited paths reference directories that exist."""
    signals: list[DriftSignal] = []
    try:
        policy = parse_repository_policy(policy_text)
    except PolicyParseError:
        signals.append(DriftSignal(
            category="policy-repo",
            severity="warn",
            message="Policy file could not be parsed; skipping path checks.",
        ))
        return signals

    for path_pattern in policy.allowed_paths:
        base = path_pattern.split("/")[0].rstrip("*")
        if not base:
            continue
        target = root / base
        if not target.exists():
            label = base if "." in base else f"{base}/"
            signals.append(DriftSignal(
                category="policy-repo",
                severity="info",
                message=f"Allowed path pattern '{path_pattern}' — '{label}' does not exist.",
            ))

    return signals


def collect_drift_signals(
    plan_text: str,
    state_text: str | None = None,
    changelog_text: str | None = None,
    policy_text: str | None = None,
    root: Path = Path("."),
) -> list[DriftSignal]:
    """Collect all drift signals without changing any files."""
    signals: list[DriftSignal] = []
    tasks = parse_plan_tasks(plan_text)

    if state_text is not None:
        state_fields = _parse_state_fields(state_text)
        signals.extend(_check_state_vs_plan(state_fields, tasks))
        signals.extend(_check_stale_state(state_fields))

    if changelog_text is not None:
        changelog_ids = _parse_changelog_task_ids(changelog_text)
        signals.extend(_check_changelog_vs_plan(changelog_ids, tasks))

    if policy_text is not None:
        signals.extend(_check_policy_path_existence(policy_text, root))

    return signals


def build_drift_report(
    plan_text: str,
    state_text: str | None = None,
    changelog_text: str | None = None,
    policy_text: str | None = None,
    root: Path = Path("."),
) -> str:
    """Return a human-readable drift report without changing files."""
    signals = collect_drift_signals(
        plan_text, state_text, changelog_text, policy_text, root
    )
    lines = [
        "Drift report",
        "Mode: read-only",
    ]
    if not signals:
        lines.append("Result: no drift detected")
    else:
        lines.append(f"Result: {len(signals)} signal(s) detected")
        for signal in signals:
            lines.append(f"[{signal.severity}] ({signal.category}) {signal.message}")
    lines.append(
        "Notes: Drift detection does not enforce corrections, change files, "
        "or run external commands."
    )
    return "\n".join(lines)


def read_drift_report(
    plan_path: Path = Path(".ai/AUTONOMOUS_PLAN.md"),
    state_path: Path = Path(".ai/AUTONOMOUS_STATE.md"),
    changelog_path: Path = Path(".ai/AUTONOMOUS_CHANGELOG.md"),
    policy_path: Path = Path(".forge/policy.md"),
    root: Path = Path("."),
) -> str:
    """Read local files and build a drift report."""
    plan_text = plan_path.read_text(encoding="utf-8")
    state_text = state_path.read_text(encoding="utf-8") if state_path.exists() else None
    changelog_text = changelog_path.read_text(encoding="utf-8") if changelog_path.exists() else None
    policy_text = policy_path.read_text(encoding="utf-8") if policy_path.exists() else None
    return build_drift_report(plan_text, state_text, changelog_text, policy_text, root)
