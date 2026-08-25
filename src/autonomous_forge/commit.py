"""Safe auto-commit with policy and validation pre-flight checks."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, replace
from pathlib import Path

from autonomous_forge.approvals import has_approval
from autonomous_forge.changelog import append_changelog_entries, find_newly_done_tasks
from autonomous_forge.diffcheck import (
    GitCommandError,
    check_diff_against_policy,
    get_changed_files,
)
from autonomous_forge.plan import (
    lint_plan_structure,
    parse_plan_tasks,
    select_eligible_task,
)
from autonomous_forge.policy import validate_policy_text
from autonomous_forge.scope import find_out_of_scope_files
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
    scope_warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CommitResult:
    """Result of a commit attempt."""

    committed: bool
    commit_hash: str
    message: str
    pre_flight: CommitPreFlight
    changelog_task_ids: tuple[str, ...] = ()


def _safe_read(path: Path) -> str | None:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def _run_git(args: list[str], root: Path) -> str:
    result = subprocess.run(  # noqa: S603 — fixed argv list, no shell/user-controlled input
        ["git"] + args,
        capture_output=True, text=True, cwd=root, timeout=30,
    )
    return result.stdout.strip()


def _git_add(path: Path, root: Path) -> bool:
    """Stage a file with `git add`, returning whether it succeeded."""
    result = subprocess.run(  # noqa: S603 — fixed argv list, no shell/user-controlled input
        ["git", "add", str(path)],  # noqa: S607 — "git" via PATH is intentional
        capture_output=True, text=True, cwd=root, timeout=30,
    )
    return result.returncode == 0


def run_pre_flight(
    root: Path = Path("."),
    plan_path: Path | None = None,
    policy_path: Path | None = None,
    validate: bool = True,
    validate_command: str | None = None,
    staged_only: bool = True,
    require_policy: bool = True,
    advisory_paths: bool = False,
    allow_shell_command: bool = False,
    require_lint_pass: bool = True,
) -> CommitPreFlight:
    """Run pre-commit safety checks: diff-check, validation, task detection."""
    plan_p = plan_path or (root / ".ai/AUTONOMOUS_PLAN.md")
    policy_p = policy_path or (root / ".forge/policy.md")
    policy_text = _safe_read(policy_p)

    task_id = ""
    task_title = ""
    approval_needed = ""
    expected_files = ""
    if plan_p.exists():
        plan_text = plan_p.read_text(encoding="utf-8")

        if require_lint_pass:
            lint_diagnostics = lint_plan_structure(plan_text)
            if lint_diagnostics:
                first = lint_diagnostics[0]
                more = f" (+{len(lint_diagnostics) - 1} more)" if len(lint_diagnostics) > 1 else ""
                return CommitPreFlight(
                    safe=False,
                    changed_files=(),
                    violations=(),
                    validation_passed=None,
                    validation_output="",
                    task_id="",
                    task_title="",
                    block_reason=(
                        f"forge lint-plan failed: line {first.line_number}: {first.message}{more} "
                        "Pass require_lint_pass=False (CLI: --no-lint-required) to override."
                    ),
                )

        tasks = parse_plan_tasks(plan_text)
        selected = select_eligible_task(tasks)
        if selected:
            task_id = selected.task_id
            task_title = selected.title
            approval_needed = selected.approval_needed
            expected_files = selected.expected_files

    if approval_needed and not has_approval(task_id, root=root):
        return CommitPreFlight(
            safe=False,
            changed_files=(),
            violations=(),
            validation_passed=None,
            validation_output="",
            task_id=task_id,
            task_title=task_title,
            block_reason=(
                f"{task_id} requires human approval: {approval_needed} "
                f"No matching record in .forge/approvals.md. "
                f'Run: forge approve {task_id} "{approval_needed}"'
            ),
        )

    try:
        changed = get_changed_files(root, staged_only=staged_only)
    except GitCommandError as exc:
        return CommitPreFlight(
            safe=False,
            changed_files=(),
            violations=(),
            validation_passed=None,
            validation_output="",
            task_id=task_id,
            task_title=task_title,
            block_reason=f"Could not determine changed files: {exc}",
        )
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

    # Advisory only (DEC-016 / AUTO-062): flags files that don't obviously
    # match the selected task's declared scope, but never blocks on it —
    # `Expected files or areas` is free-form prose written by whoever
    # authored the task, not a strict policy, and a mismatch is just as
    # likely to mean the wrong task got auto-selected as it is to mean the
    # diff is actually wrong.
    scope_warnings = find_out_of_scope_files(changed, expected_files)

    if require_policy:
        policy_problem = validate_policy_text(policy_text)
        if policy_problem:
            return CommitPreFlight(
                safe=False,
                changed_files=tuple(changed),
                violations=(),
                validation_passed=None,
                validation_output="",
                task_id=task_id,
                task_title=task_title,
                block_reason=(
                    f"Policy required but {policy_problem}: {policy_p}. "
                    "Pass require_policy=False (CLI: --no-policy-required) to override."
                ),
                scope_warnings=scope_warnings,
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
                scope_warnings=scope_warnings,
            )
        violations_list = [
            f"[{v.rule}] {v.path}: {v.message}" for v in diff_violations
        ]
        not_allowed = [v for v in diff_violations if v.rule == "not-allowed"]
        if not_allowed and not advisory_paths:
            return CommitPreFlight(
                safe=False,
                changed_files=tuple(changed),
                violations=tuple(violations_list),
                validation_passed=None,
                validation_output="",
                task_id=task_id,
                task_title=task_title,
                block_reason=(
                    f"File(s) outside allowed paths: {', '.join(v.path for v in not_allowed)}. "
                    "Pass --advisory-paths to report only, or widen .forge/policy.md's Allowed paths."
                ),
                scope_warnings=scope_warnings,
            )

    validation_passed = None
    validation_output = ""
    if validate:
        val_result = run_validation(
            root,
            command=validate_command,
            policy_path=policy_p,
            allow_shell_command=allow_shell_command,
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
                scope_warnings=scope_warnings,
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
        scope_warnings=scope_warnings,
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
    timestamp: str | None = None,
    require_policy: bool = True,
    advisory_paths: bool = False,
    allow_shell_command: bool = False,
    require_lint_pass: bool = True,
) -> CommitResult:
    """Run pre-flight checks and commit if safe.

    Before committing, appends one changelog line per task whose Status
    just flipped to DONE (compared to HEAD) and stages that change, so it
    lands in the same commit — see `autonomous_forge.changelog`.
    """
    if pre_flight is None:
        pre_flight = run_pre_flight(
            root, plan_path=plan_path, policy_path=policy_path,
            validate=validate, validate_command=validate_command,
            staged_only=staged_only, require_policy=require_policy,
            advisory_paths=advisory_paths, allow_shell_command=allow_shell_command,
            require_lint_pass=require_lint_pass,
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

    newly_done = find_newly_done_tasks(root, plan_path=plan_path)
    changelog_task_ids: tuple[str, ...] = ()
    if newly_done:
        changelog_p = append_changelog_entries(newly_done, root=root, timestamp=timestamp)
        if changelog_p is not None:
            changelog_task_ids = tuple(t.task_id for t in newly_done)
            if not _git_add(changelog_p, root):
                return CommitResult(
                    committed=False,
                    commit_hash="",
                    message=f"git add failed for {changelog_p}",
                    pre_flight=pre_flight,
                )

            # Re-validate the diff/policy check against the tree that will
            # actually be committed, now that the changelog is staged too —
            # the original pre-flight above ran before this file existed in
            # the diff, so a policy that disallows this path must still be
            # able to block it here instead of silently letting it through
            # (AUTO-061 / SEC-005).
            policy_p = policy_path or (root / ".forge/policy.md")
            policy_text = _safe_read(policy_p)
            if policy_text:
                try:
                    changed_after = get_changed_files(root, staged_only=staged_only)
                except GitCommandError as exc:
                    return CommitResult(
                        committed=False,
                        commit_hash="",
                        message=(
                            "Could not re-validate staged changes after "
                            f"changelog update: {exc}"
                        ),
                        pre_flight=pre_flight,
                    )
                diff_violations = check_diff_against_policy(changed_after, policy_text)
                prohibited = [v for v in diff_violations if v.rule == "prohibited"]
                not_allowed = [v for v in diff_violations if v.rule == "not-allowed"]
                blocking = [*prohibited, *(not_allowed if not advisory_paths else [])]
                if blocking:
                    updated_pre_flight = replace(
                        pre_flight,
                        changed_files=tuple(changed_after),
                        violations=tuple(
                            f"[{v.rule}] {v.path}: {v.message}" for v in diff_violations
                        ),
                        safe=False,
                        block_reason=(
                            "Changelog update violates policy: "
                            f"{', '.join(v.path for v in blocking)}"
                        ),
                    )
                    return CommitResult(
                        committed=False,
                        commit_hash="",
                        message=updated_pre_flight.block_reason,
                        pre_flight=updated_pre_flight,
                    )

    try:
        result = subprocess.run(  # noqa: S603 — fixed argv list, no shell/user-controlled input
            ["git", "commit", "-m", message],  # noqa: S607 — "git" via PATH is intentional
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
        changelog_task_ids=changelog_task_ids,
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

    if pf.scope_warnings:
        lines.append(
            f"Scope warning: {len(pf.scope_warnings)} changed file(s) don't match "
            f"{pf.task_id}'s declared Expected files or areas (advisory only, does not block):"
        )
        for f in pf.scope_warnings:
            lines.append(f"  {f}")

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
        if result.changelog_task_ids:
            lines.append(f"Changelog updated: {', '.join(result.changelog_task_ids)}")
    elif result.pre_flight.block_reason:
        lines.append(f"\nNot committed: {result.pre_flight.block_reason}")
    else:
        lines.append(f"\nNot committed: {result.message}")
    return "\n".join(lines)
