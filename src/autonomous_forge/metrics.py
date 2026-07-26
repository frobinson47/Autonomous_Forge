"""Aggregate metrics from forge run history."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from autonomous_forge.log import list_runs


@dataclass(frozen=True)
class RunMetrics:
    """Aggregate stats from run history."""

    total_runs: int
    passed: int
    failed: int
    blocked: int
    skipped: int
    unique_tasks: int
    total_files_changed: int
    total_violations: int
    total_drift_signals: int
    pass_rate: float


def compute_metrics(root: Path = Path("."), limit: int = 1000) -> RunMetrics:
    """Compute aggregate metrics from run history."""
    entries = list_runs(root, limit=limit)

    if not entries:
        return RunMetrics(
            total_runs=0, passed=0, failed=0, blocked=0, skipped=0,
            unique_tasks=0, total_files_changed=0, total_violations=0,
            total_drift_signals=0, pass_rate=0.0,
        )

    passed = sum(1 for e in entries if e.validation == "PASSED")
    failed = sum(1 for e in entries if e.validation == "FAILED")
    blocked = sum(1 for e in entries if e.blocked)
    skipped = sum(1 for e in entries if e.validation in ("skipped", "skipped (dry run)", ""))
    tasks = {e.task for e in entries if e.task and e.task != "none"}
    files = sum(e.changed_files for e in entries)
    violations = sum(e.diff_violations for e in entries)
    drift = sum(e.drift_signals for e in entries)

    validated = passed + failed
    rate = (passed / validated * 100) if validated > 0 else 0.0

    return RunMetrics(
        total_runs=len(entries),
        passed=passed,
        failed=failed,
        blocked=blocked,
        skipped=skipped,
        unique_tasks=len(tasks),
        total_files_changed=files,
        total_violations=violations,
        total_drift_signals=drift,
        pass_rate=round(rate, 1),
    )


def format_metrics_json(m: RunMetrics) -> str:
    """Format metrics as a versioned JSON string for programmatic consumption.

    Same fields and values as `format_metrics` — a different output format
    of the same data, not a different computation. See `export.py`'s
    `version` convention: bump this if a field is ever removed or a
    meaning changes, not for additive fields.
    """
    data = {
        "version": "1",
        "total_runs": m.total_runs,
        "passed": m.passed,
        "failed": m.failed,
        "blocked": m.blocked,
        "skipped": m.skipped,
        "unique_tasks": m.unique_tasks,
        "total_files_changed": m.total_files_changed,
        "total_violations": m.total_violations,
        "total_drift_signals": m.total_drift_signals,
        "pass_rate": m.pass_rate,
    }
    return json.dumps(data, indent=2)


def format_metrics(m: RunMetrics) -> str:
    """Format metrics as a concise report."""
    if m.total_runs == 0:
        return "No run history found."

    lines = [
        "Forge metrics",
        f"Total runs: {m.total_runs}",
        f"Passed: {m.passed}  Failed: {m.failed}  Blocked: {m.blocked}  Skipped: {m.skipped}",
        f"Pass rate: {m.pass_rate}%",
        f"Unique tasks: {m.unique_tasks}",
        f"Files changed: {m.total_files_changed}",
        f"Violations: {m.total_violations}",
        f"Drift signals: {m.total_drift_signals}",
    ]
    return "\n".join(lines)
