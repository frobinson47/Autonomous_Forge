"""Safe auto-commit with policy and validation pre-flight checks."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from autonomous_forge.diffcheck import check_diff_against_policy, get_changed_files
from autonomous_forge.plan import parse_plan_tasks, select_eligible_task
from autonomous_forge.validate import run_validation


@dataclass(frozen=True)
class CommitPreFlight:
    """Result of pre-commit safety checks."""

    safe: bool
    changed_files: tuple[str, ...]
    violations: tuple[str, ...]
    validation_passed: bool | None
    validation_output: str
    task_id: str
    task_title: str
    block_reason: str


@dataclass(frozen=True)
class CommitResult:
    """Result of a commit attempt."""

    committed: bool
    commit_hash: str
    message: str
    pre_flight: CommitPreFlight


def _safe_read(path: Path) -> str | None:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def _run_git(args: list[str], root: Path) -> str:
    result = subprocess.run(
        ["git"] + args,
        capture_output=True, text=True, cwd=root, timeout=30,
    )
    return result.stdout.strip()


def run_pre_flight(
    root: Path = Path("."),
    plan_path: Path | None = None,
    policy_path: Path | None = None,
    validate: bool = True,
    validate_command: str | None = None,
    staged_only: bool = True,
) -> CommitPreFlight:
    """Run pre-commit safety checks: diff-check, validation, task detection."""
    plan_p = plan_path or (root / ".ai/AUTONOMOUS_PLAN.md")
    policy_p = policy_path or (root / ".forge/policy.md")
    policy_text = _safe_read(policy_p)

    task_id = ""
    task_title = ""
    if plan_p.exists():
        plan_text = plan_p.read_text(encoding="utf-8")
        tasks = parse_plan_tasks(plan_text)
        selected = select_eligible_task(tasks)
        if selected:
            task_id = selected.task_id
            task_title = selected.title

    changed = get_changed_files(root, staged_only=staged_only)
    if not changed:
        return CommitPreFlight(
            safe=False,
            changed_files=(),
            violations=(),
            validation_passed=None,
            validation_output="",
            task_id=task_id,
            task_title=task_title,
            block_reason="No changed files to commit.",
        )

    violations_list: list[str] = []
    if policy_text:
        diff_violations = check_diff_against_policy(changed, policy_text)
        prohibited = [v for v in diff_violations if v.rule == "prohibited"]
        if prohibited:
            violations_list = [
                f"[{v.rule}] {v.path}: {v.message}" for v in diff_violations
            ]
            return CommitPreFlight(
                safe=False,
                changed_files=tuple(changed),
                violations=tuple(violations_list),
                validation_passed=None,
                validation_output="",
                task_id=task_id,
                task_title=task_title,
                block_reason=f"Prohibited file(s): {', '.join(v.path for v in prohibited)}",
            )
        violations_list = [
            f"[{v.rule}] {v.path}: {v.message}" for v in diff_violations
        ]

    validation_passed = None
    validation_output = ""
    if validate:
        val_result = run_validation(
            root,
            command=validate_command,
            policy_path=policy_p,
        )
        validation_passed = val_result.passed
        output_lines = val_result.stdout.strip().splitlines()
        if len(output_lines) > 10:
            validation_output = "\n".join(output_lines[-10:])
        else:
            validation_output = val_result.stdout.strip()

        if not val_result.passed:
            return CommitPreFlight(
                safe=False,
                changed_files=tuple(changed),
                violations=tuple(violations_list),
                validation_passed=False,
                validation_output=validation_output,
                task_id=task_id,
                task_title=task_title,
                block_reason="Validation failed.",
            )

    return CommitPreFlight(
        safe=True,
        changed_files=tuple(changed),
        violations=tuple(violations_list),
        validation_passed=validation_passed,
        validation_output=validation_output,
        task_id=task_id,
        task_title=task_title,
        block_reason="",
    )


def execute_commit(
    root: Path = Path("."),
    message: str | None = None,
    pre_flight: CommitPreFlight | None = None,
    plan_path: Path | None = None,
    policy_path: Path | None = None,
    validate: bool = True,
    validate_command: str | None = None,
    staged_only: bool = True,
) -> CommitResult:
    """Run pre-flight checks and commit if safe."""
    if pre_flight is None:
        pre_flight = run_pre_flight(
            root, plan_path=plan_path, policy_path=policy_path,
            validate=validate, validate_command=validate_command,
            staged_only=staged_only,
        )

    if not pre_flight.safe:
        return CommitResult(
            committed=False,
            commit_hash="",
            message=pre_flight.block_reason,
            pre_flight=pre_flight,
        )

    if message is None:
        if pre_flight.task_id:
            message = f"forge: {pre_flight.task_id} — {pre_flight.task_title}"
        else:
            message = "forge: autonomous commit"

    try:
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True, text=True, cwd=root, timeout=30,
        )
        if result.returncode != 0:
            return CommitResult(
                committed=False,
                commit_hash="",
                message=f"git commit failed: {result.stderr.strip()}",
                pre_flight=pre_flight,
            )
        commit_hash = _run_git(["rev-parse", "--short", "HEAD"], root)
    except subprocess.SubprocessError as exc:
        return CommitResult(
            committed=False,
            commit_hash="",
            message=f"git error: {exc}",
            pre_flight=pre_flight,
        )

    return CommitResult(
        committed=True,
        commit_hash=commit_hash,
        message=message,
        pre_flight=pre_flight,
    )


def format_pre_flight(pf: CommitPreFlight) -> str:
    """Format pre-flight results as a human-readable report."""
    lines = ["Forge commit pre-flight"]

    if pf.task_id:
        lines.append(f"Task: {pf.task_id} — {pf.task_title}")

    lines.append(f"Changed files: {len(pf.changed_files)}")
    if pf.changed_files:
        for f in pf.changed_files:
            lines.append(f"  {f}")

    if pf.violations:
        lines.append(f"Policy violations: {len(pf.violations)}")
        for v in pf.violations:
            lines.append(f"  {v}")

    if pf.validation_passed is not None:
        status = "PASSED" if pf.validation_passed else "FAILED"
        lines.append(f"Validation: {status}")

    if pf.safe:
        lines.append("Result: SAFE to commit")
    else:
        lines.append(f"Result: BLOCKED — {pf.block_reason}")

    return "\n".join(lines)


def format_commit_result(result: CommitResult) -> str:
    """Format a commit result."""
    lines = [format_pre_flight(result.pre_flight)]
    if result.committed:
        lines.append(f"\nCommitted: {result.commit_hash}")
        lines.append(f"Message: {result.message}")
    elif result.pre_flight.block_reason:
        lines.append(f"\nNot committed: {result.pre_flight.block_reason}")
    else:
        lines.append(f"\nNot committed: {result.message}")
    return "\n".join(lines)
