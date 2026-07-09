"""Forge check — run all verification steps in one command."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from autonomous_forge.diffcheck import check_diff_against_policy, get_changed_files
from autonomous_forge.drift import collect_drift_signals
from autonomous_forge.plan import (
    PlanParseError,
    lint_plan_structure,
    parse_plan_tasks,
)
from autonomous_forge.validate import run_validation


@dataclass(frozen=True)
class CheckResult:
    """Combined result of all verification steps."""

    lint_ok: bool
    lint_diagnostics: tuple[str, ...]
    drift_ok: bool
    drift_signals: tuple[str, ...]
    diff_ok: bool
    diff_violations: tuple[str, ...]
    validation_ok: bool | None
    validation_output: str
    all_passed: bool


def execute_check(
    root: Path = Path("."),
    plan_path: Path | None = None,
    policy_path: Path | None = None,
    validate: bool = True,
    validate_command: str | None = None,
    timeout: int = 300,
) -> CheckResult:
    """Run lint, drift, diff-check, and validation."""
    plan = plan_path or root / ".ai" / "AUTONOMOUS_PLAN.md"
    policy = policy_path or root / ".forge" / "policy.md"
    state = root / ".ai" / "AUTONOMOUS_STATE.md"
    changelog = root / ".ai" / "AUTONOMOUS_CHANGELOG.md"

    # Lint
    lint_diags: list[str] = []
    lint_ok = True
    try:
        text = plan.read_text(encoding="utf-8")
        diags = lint_plan_structure(text)
        if diags:
            lint_ok = False
            lint_diags = [f"line {d.line_number}: {d.message}" for d in diags]
    except FileNotFoundError:
        lint_ok = False
        lint_diags = [f"Plan not found: {plan}"]

    # Drift
    drift_msgs: list[str] = []
    drift_ok = True
    try:
        plan_text_drift = plan.read_text(encoding="utf-8")
        state_text = state.read_text(encoding="utf-8") if state.exists() else None
        changelog_text = changelog.read_text(encoding="utf-8") if changelog.exists() else None
        policy_text_drift = policy.read_text(encoding="utf-8") if policy.exists() else None
        signals = collect_drift_signals(
            plan_text_drift,
            state_text=state_text,
            changelog_text=changelog_text,
            policy_text=policy_text_drift,
            root=root,
        )
        error_signals = [s for s in signals if s.severity == "error"]
        if error_signals:
            drift_ok = False
            drift_msgs = [f"[{s.severity}] ({s.category}) {s.message}" for s in error_signals]
        elif signals:
            drift_msgs = [f"[{s.severity}] ({s.category}) {s.message}" for s in signals]
    except (FileNotFoundError, PlanParseError):
        pass

    # Diff-check
    diff_violations: list[str] = []
    diff_ok = True
    try:
        if policy.exists():
            policy_text = policy.read_text(encoding="utf-8")
            changed = get_changed_files(root)
            violations = check_diff_against_policy(changed, policy_text)
            if violations:
                diff_ok = False
                diff_violations = [f"{v.path}: {v.message}" for v in violations]
    except Exception:
        pass

    # Validation
    val_ok: bool | None = None
    val_output = ""
    if validate:
        result = run_validation(
            root,
            command=validate_command,
            policy_path=policy,
            timeout_seconds=timeout,
        )
        val_ok = result.passed
        val_output = result.stdout or ""

    all_passed = lint_ok and drift_ok and diff_ok and (val_ok is not False)

    return CheckResult(
        lint_ok=lint_ok,
        lint_diagnostics=tuple(lint_diags),
        drift_ok=drift_ok,
        drift_signals=tuple(drift_msgs),
        diff_ok=diff_ok,
        diff_violations=tuple(diff_violations),
        validation_ok=val_ok,
        validation_output=val_output,
        all_passed=all_passed,
    )


def format_check_result(result: CheckResult) -> str:
    """Format check result as a concise report."""
    lines = ["Forge check"]

    lines.append(f"Lint: {'PASS' if result.lint_ok else 'FAIL'}")
    for d in result.lint_diagnostics:
        lines.append(f"  {d}")

    lines.append(f"Drift: {'PASS' if result.drift_ok else 'FAIL'}")
    for s in result.drift_signals:
        lines.append(f"  {s}")

    lines.append(f"Diff-check: {'PASS' if result.diff_ok else 'FAIL'}")
    for v in result.diff_violations:
        lines.append(f"  {v}")

    if result.validation_ok is None:
        lines.append("Validation: skipped")
    else:
        lines.append(f"Validation: {'PASS' if result.validation_ok else 'FAIL'}")

    lines.append(f"Result: {'ALL PASSED' if result.all_passed else 'ISSUES FOUND'}")
    return "\n".join(lines)
