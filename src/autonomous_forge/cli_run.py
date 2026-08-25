"""CLI commands for running/validating/committing work: run, commit, push,
pipeline, check, watch, validate, diff-check, revert, log, approve.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from autonomous_forge.approvals import format_approval_confirmation, record_approval
from autonomous_forge.check import execute_check, format_check_result
from autonomous_forge.commit import (
    execute_commit,
    format_commit_result,
    format_pre_flight,
    run_pre_flight,
)
from autonomous_forge.diffcheck import read_diff_report
from autonomous_forge.log import format_run_log, list_runs
from autonomous_forge.pipeline import execute_pipeline, format_pipeline_result
from autonomous_forge.push import execute_push, format_push_result
from autonomous_forge.revert import execute_revert, format_revert_result
from autonomous_forge.run import execute_run, format_run_outcome, save_run_outcome
from autonomous_forge.validate import format_validation_result, run_validation
from autonomous_forge.watch import run_watch


def add_run_parsers(subparsers: argparse._SubParsersAction) -> None:
    """Add the run/commit/push/pipeline/check/watch/validate/diff-check/revert/log/approve parsers."""
    diffcheck_parser = subparsers.add_parser(
        "diff-check",
        help="validate changed files against repository policy",
    )
    diffcheck_parser.add_argument(
        "--root",
        default=".",
        help="repository root",
    )
    diffcheck_parser.add_argument(
        "--policy",
        default=None,
        help="path to the repository policy file",
    )
    diffcheck_parser.add_argument(
        "--staged",
        action="store_true",
        help="check only staged files",
    )

    run_parser = subparsers.add_parser(
        "run",
        help="execute one autonomous cycle: select, validate, diff-check, record",
    )
    run_parser.add_argument(
        "--root",
        default=".",
        help="repository root",
    )
    run_parser.add_argument(
        "--plan",
        default=None,
        help="path to the autonomous roadmap file",
    )
    run_parser.add_argument(
        "--policy",
        default=None,
        help="path to the repository policy file",
    )
    run_parser.add_argument(
        "--cmd",
        default=None,
        dest="run_cmd",
        help="validation command override",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="skip validation execution",
    )
    run_parser.add_argument(
        "--no-validate",
        action="store_true",
        help="skip validation entirely",
    )
    run_parser.add_argument(
        "--no-save",
        action="store_true",
        help="do not persist the run outcome to .forge/runs/",
    )
    run_parser.add_argument(
        "--no-persist-output",
        action="store_true",
        help=(
            "persist the run outcome as usual, but omit the raw validation "
            "output block (task/policy/diff info is still saved)"
        ),
    )
    run_parser.add_argument(
        "--no-policy-required",
        action="store_true",
        help="allow a missing or malformed policy file instead of blocking (default: blocks)",
    )
    run_parser.add_argument(
        "--advisory-paths",
        action="store_true",
        help="report files outside Allowed paths instead of blocking (default: blocks)",
    )
    run_parser.add_argument(
        "--allow-shell-command",
        action="store_true",
        help="allow the validation command to run through the shell (pipes, redirects, chaining); default rejects such commands",
    )
    run_parser.add_argument(
        "--no-lint-required",
        action="store_true",
        help="allow a plan with forge lint-plan diagnostics instead of blocking (default: blocks)",
    )
    run_parser.add_argument(
        "--timestamp",
        default=None,
        help="optional ISO-8601 timestamp for deterministic output",
    )

    commit_parser = subparsers.add_parser(
        "commit",
        help="safe auto-commit with policy and validation pre-flight",
    )
    commit_parser.add_argument(
        "--root",
        default=".",
        help="repository root",
    )
    commit_parser.add_argument(
        "--plan",
        default=None,
        help="path to the autonomous roadmap file",
    )
    commit_parser.add_argument(
        "--policy",
        default=None,
        help="path to the repository policy file",
    )
    commit_parser.add_argument(
        "--message", "-m",
        default=None,
        help="commit message (auto-generated from task if omitted)",
    )
    commit_parser.add_argument(
        "--cmd",
        default=None,
        dest="commit_cmd",
        help="validation command override",
    )
    commit_parser.add_argument(
        "--no-validate",
        action="store_true",
        help="skip validation",
    )
    commit_parser.add_argument(
        "--check-only",
        action="store_true",
        help="run pre-flight checks only, do not commit",
    )
    commit_parser.add_argument(
        "--no-policy-required",
        action="store_true",
        help="allow a missing or malformed policy file instead of blocking (default: blocks)",
    )
    commit_parser.add_argument(
        "--advisory-paths",
        action="store_true",
        help="report files outside Allowed paths instead of blocking (default: blocks)",
    )
    commit_parser.add_argument(
        "--allow-shell-command",
        action="store_true",
        help="allow the validation command to run through the shell (pipes, redirects, chaining); default rejects such commands",
    )
    commit_parser.add_argument(
        "--no-lint-required",
        action="store_true",
        help="allow a plan with forge lint-plan diagnostics instead of blocking (default: blocks)",
    )

    push_parser = subparsers.add_parser(
        "push",
        help="push local commits to the git remote",
    )
    push_parser.add_argument(
        "--root",
        default=".",
        help="repository root",
    )
    push_parser.add_argument(
        "--remote",
        default="origin",
        help="git remote to push to (default: origin)",
    )

    log_parser = subparsers.add_parser(
        "log",
        help="show run history from .forge/runs/",
    )
    log_parser.add_argument(
        "--root",
        default=".",
        help="repository root",
    )
    log_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="max runs to show (default: 20)",
    )
    log_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="show detailed info per run",
    )

    pipeline_parser = subparsers.add_parser(
        "pipeline",
        help="full autonomous pipeline: run -> commit -> push -> sync",
    )
    pipeline_parser.add_argument(
        "--root",
        default=".",
        help="repository root",
    )
    pipeline_parser.add_argument(
        "--plan",
        default=None,
        help="path to the autonomous roadmap file",
    )
    pipeline_parser.add_argument(
        "--policy",
        default=None,
        help="path to the repository policy file",
    )
    pipeline_parser.add_argument(
        "--cmd",
        default=None,
        dest="pipeline_cmd",
        help="validation command override",
    )
    pipeline_parser.add_argument(
        "--commit",
        action="store_true",
        help="auto-commit if checks pass (opt-in)",
    )
    pipeline_parser.add_argument(
        "--push",
        action="store_true",
        help="push commits to the git remote after commit (opt-in)",
    )
    pipeline_parser.add_argument(
        "--sync",
        action="store_true",
        help="sync Forgejo issue status after push (opt-in)",
    )
    pipeline_parser.add_argument(
        "-m", "--message",
        default=None,
        dest="pipeline_message",
        help="commit message override",
    )
    pipeline_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="skip validation execution",
    )
    pipeline_parser.add_argument(
        "--no-policy-required",
        action="store_true",
        help="allow a missing or malformed policy file instead of blocking (default: blocks)",
    )
    pipeline_parser.add_argument(
        "--advisory-paths",
        action="store_true",
        help="report files outside Allowed paths instead of blocking (default: blocks)",
    )
    pipeline_parser.add_argument(
        "--allow-shell-command",
        action="store_true",
        help="allow the validation command to run through the shell (pipes, redirects, chaining); default rejects such commands",
    )
    pipeline_parser.add_argument(
        "--no-lint-required",
        action="store_true",
        help="allow a plan with forge lint-plan diagnostics instead of blocking (default: blocks)",
    )
    pipeline_parser.add_argument(
        "--no-persist-output",
        action="store_true",
        help=(
            "persist the run outcome as usual, but omit the raw validation "
            "output block (task/policy/diff info is still saved)"
        ),
    )
    pipeline_parser.add_argument(
        "--timestamp",
        default=None,
        help="optional ISO-8601 timestamp for deterministic output",
    )

    approve_parser = subparsers.add_parser(
        "approve",
        help="record a human approval for a task's 'Approval needed' category (see DEC-013)",
    )
    approve_parser.add_argument(
        "task_id",
        help="task ID (e.g. AUTO-001)",
    )
    approve_parser.add_argument(
        "category",
        help="the approval-required category text being approved",
    )
    approve_parser.add_argument(
        "--note",
        default="",
        help="optional note explaining why this was approved",
    )
    approve_parser.add_argument(
        "--root",
        default=".",
        help="repository root",
    )

    revert_parser = subparsers.add_parser(
        "revert",
        help="undo a completed task's commit and flip its status back to TODO",
    )
    revert_parser.add_argument(
        "task_id",
        help="task ID (e.g. AUTO-001)",
    )
    revert_parser.add_argument(
        "--root",
        default=".",
        help="repository root",
    )
    revert_parser.add_argument(
        "--plan",
        default=None,
        help="path to the autonomous roadmap file",
    )
    revert_parser.add_argument(
        "--commit",
        default=None,
        dest="revert_commit",
        help="commit hash to revert, overriding the one recorded in run history",
    )

    check_parser = subparsers.add_parser(
        "check",
        help="run all verification steps: lint, drift, diff-check, validate",
    )
    check_parser.add_argument(
        "--root",
        default=".",
        help="repository root",
    )
    check_parser.add_argument(
        "--plan",
        default=None,
        help="path to the autonomous roadmap file",
    )
    check_parser.add_argument(
        "--policy",
        default=None,
        help="path to the repository policy file",
    )
    check_parser.add_argument(
        "--cmd",
        default=None,
        dest="check_cmd",
        help="validation command override",
    )
    check_parser.add_argument(
        "--no-validate",
        action="store_true",
        help="skip validation",
    )
    check_parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="validation timeout in seconds (default: 300)",
    )
    check_parser.add_argument(
        "--no-policy-required",
        action="store_true",
        help="don't fail closed when the policy file is missing or malformed",
    )

    watch_parser = subparsers.add_parser(
        "watch",
        help="periodically re-run forge check until interrupted",
    )
    watch_parser.add_argument(
        "--root",
        default=".",
        help="repository root",
    )
    watch_parser.add_argument(
        "--plan",
        default=None,
        help="path to the autonomous roadmap file",
    )
    watch_parser.add_argument(
        "--policy",
        default=None,
        help="path to the repository policy file",
    )
    watch_parser.add_argument(
        "--cmd",
        default=None,
        dest="watch_cmd",
        help="validation command override",
    )
    watch_parser.add_argument(
        "--no-validate",
        action="store_true",
        help="skip validation",
    )
    watch_parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="validation timeout in seconds (default: 300)",
    )
    watch_parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="seconds between check cycles (default: 300)",
    )
    watch_parser.add_argument(
        "--once",
        action="store_true",
        help="run a single check cycle and exit",
    )
    watch_parser.add_argument(
        "--no-policy-required",
        action="store_true",
        help="don't fail closed when the policy file is missing or malformed",
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="run validation command and report results",
    )
    validate_parser.add_argument(
        "--root",
        default=".",
        help="repository root",
    )
    validate_parser.add_argument(
        "--cmd",
        default=None,
        dest="validate_cmd",
        help="validation command (defaults to policy expectation or pytest)",
    )
    validate_parser.add_argument(
        "--policy",
        default=None,
        help="path to the repository policy file",
    )
    validate_parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="timeout in seconds (default: 300)",
    )
    validate_parser.add_argument(
        "--allow-shell-command",
        action="store_true",
        help="allow the validation command to run through the shell (pipes, redirects, chaining); default rejects such commands",
    )


def _cmd_run(args: argparse.Namespace) -> int:
    root = Path(args.root)
    plan_path = Path(args.plan) if args.plan else None
    policy_path = Path(args.policy) if args.policy else None
    try:
        outcome = execute_run(
            root,
            plan_path=plan_path,
            policy_path=policy_path,
            validate=not args.no_validate,
            validate_command=args.run_cmd,
            dry_run=args.dry_run,
            timestamp=args.timestamp,
            require_policy=not args.no_policy_required,
            advisory_paths=args.advisory_paths,
            allow_shell_command=args.allow_shell_command,
            require_lint_pass=not args.no_lint_required,
        )
    except FileNotFoundError as exc:
        print(f"File not found: {exc}")
        return 2
    print(format_run_outcome(outcome))
    if not args.no_save:
        path = save_run_outcome(outcome, root, persist_output=not args.no_persist_output)
        print(f"\nRun saved: {path}")
    return 1 if outcome.blocked else 0


def _cmd_pipeline(args: argparse.Namespace) -> int:
    root = Path(args.root)
    plan_path = Path(args.plan) if args.plan else None
    policy_path = Path(args.policy) if args.policy else None
    try:
        result = execute_pipeline(
            root,
            plan_path=plan_path,
            policy_path=policy_path,
            validate_command=args.pipeline_cmd,
            commit=args.commit,
            push=args.push,
            sync=args.sync,
            commit_message=args.pipeline_message,
            dry_run=args.dry_run,
            timestamp=args.timestamp,
            require_policy=not args.no_policy_required,
            advisory_paths=args.advisory_paths,
            allow_shell_command=args.allow_shell_command,
            require_lint_pass=not args.no_lint_required,
            persist_output=not args.no_persist_output,
        )
    except FileNotFoundError as exc:
        print(f"File not found: {exc}")
        return 2
    print(format_pipeline_result(result))
    if result.run_outcome and result.run_outcome.blocked:
        return 1
    if result.commit_result and not result.commit_result.committed and args.commit:
        return 1
    if result.push_result and not result.push_result.pushed and args.push:
        return 1
    if result.sync_result and result.sync_result.errors:
        return 1
    return 0


def _cmd_log(args: argparse.Namespace) -> int:
    entries = list_runs(Path(args.root), limit=args.limit)
    print(format_run_log(entries, verbose=args.verbose))
    return 0


def _cmd_commit(args: argparse.Namespace) -> int:
    root = Path(args.root)
    plan_path = Path(args.plan) if args.plan else None
    policy_path = Path(args.policy) if args.policy else None
    if args.check_only:
        pf = run_pre_flight(
            root, plan_path=plan_path, policy_path=policy_path,
            validate=not args.no_validate,
            validate_command=args.commit_cmd,
            require_policy=not args.no_policy_required,
            advisory_paths=args.advisory_paths,
            allow_shell_command=args.allow_shell_command,
            require_lint_pass=not args.no_lint_required,
        )
        print(format_pre_flight(pf))
        return 0 if pf.safe else 1
    result = execute_commit(
        root, message=args.message,
        plan_path=plan_path, policy_path=policy_path,
        validate=not args.no_validate,
        validate_command=args.commit_cmd,
        require_policy=not args.no_policy_required,
        advisory_paths=args.advisory_paths,
        allow_shell_command=args.allow_shell_command,
        require_lint_pass=not args.no_lint_required,
    )
    print(format_commit_result(result))
    return 0 if result.committed else 1


def _cmd_push(args: argparse.Namespace) -> int:
    result = execute_push(root=Path(args.root), remote=args.remote)
    print(format_push_result(result))
    return 0 if result.pushed else 1


def _cmd_approve(args: argparse.Namespace) -> int:
    path = record_approval(
        args.task_id, args.category,
        root=Path(args.root), note=args.note,
    )
    print(format_approval_confirmation(args.task_id, args.category, path))
    return 0


def _cmd_revert(args: argparse.Namespace) -> int:
    root = Path(args.root)
    plan_path = Path(args.plan) if args.plan else None
    result = execute_revert(
        args.task_id, root, plan_path=plan_path, commit_override=args.revert_commit,
    )
    print(format_revert_result(result))
    return 0 if result.reverted else 1


def _cmd_check(args: argparse.Namespace) -> int:
    root = Path(args.root)
    plan_path = Path(args.plan) if args.plan else None
    policy_path = Path(args.policy) if args.policy else None
    result = execute_check(
        root,
        plan_path=plan_path,
        policy_path=policy_path,
        validate=not args.no_validate,
        validate_command=args.check_cmd,
        timeout=args.timeout,
        require_policy=not args.no_policy_required,
    )
    print(format_check_result(result))
    return 0 if result.all_passed else 1


def _cmd_watch(args: argparse.Namespace) -> int:
    root = Path(args.root)
    plan_path = Path(args.plan) if args.plan else None
    policy_path = Path(args.policy) if args.policy else None
    return run_watch(
        root,
        plan_path=plan_path,
        policy_path=policy_path,
        validate=not args.no_validate,
        validate_command=args.watch_cmd,
        timeout=args.timeout,
        interval=args.interval,
        once=args.once,
        require_policy=not args.no_policy_required,
    )


def _cmd_diff_check(args: argparse.Namespace) -> int:
    root = Path(args.root)
    policy_path = Path(args.policy) if args.policy else None
    report = read_diff_report(root, policy_path=policy_path, staged_only=args.staged)
    print(report)
    return 1 if "could not inspect changes" in report else 0


def _cmd_validate(args: argparse.Namespace) -> int:
    root = Path(args.root)
    policy_path = Path(args.policy) if args.policy else None
    result = run_validation(
        root, command=args.validate_cmd,
        policy_path=policy_path, timeout_seconds=args.timeout,
        allow_shell_command=args.allow_shell_command,
    )
    print(format_validation_result(result))
    return 0 if result.passed else 1
