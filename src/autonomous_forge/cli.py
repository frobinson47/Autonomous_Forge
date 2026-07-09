"""Command-line interface for Autonomous Forge."""

from __future__ import annotations

import argparse
from pathlib import Path

from autonomous_forge.commit import (
    execute_commit,
    format_commit_result,
    format_pre_flight,
    run_pre_flight,
)
from autonomous_forge.context import build_project_context
from autonomous_forge.diffcheck import read_diff_report
from autonomous_forge.drift import read_drift_report
from autonomous_forge.init import format_init_result, init_forge
from autonomous_forge.log import format_run_log, list_runs
from autonomous_forge.mark import format_mark_result, mark_task_status
from autonomous_forge.status import get_status
from autonomous_forge.pipeline import execute_pipeline, format_pipeline_result
from autonomous_forge.inventory import build_repository_inventory
from autonomous_forge.run import execute_run, format_run_outcome, save_run_outcome
from autonomous_forge.sync import execute_sync, format_sync_result
from autonomous_forge.validate import format_validation_result, run_validation
from autonomous_forge.session import (
    build_session_snapshot,
    capture_git_snapshot,
    format_resume_briefing,
    load_latest_session,
    save_session,
)
from autonomous_forge.plan import (
    PlanParseError,
    PlanSelectionError,
    lint_plan_structure,
    parse_plan_tasks,
    select_eligible_task,
)
from autonomous_forge.policy import PolicyParseError, RepositoryPolicy, parse_repository_policy
from autonomous_forge.report import read_repository_report
from autonomous_forge.run_summary import read_run_summary_preview


def build_parser() -> argparse.ArgumentParser:
    """Build the Forge command parser."""
    parser = argparse.ArgumentParser(
        prog="forge",
        description=(
            "Run local-first, dry-run checks for safe autonomous "
            "repository maintenance loops."
        ),
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="show the installed Autonomous Forge version and exit",
    )

    subparsers = parser.add_subparsers(dest="command")
    tasks_parser = subparsers.add_parser(
        "tasks",
        help="parse roadmap task headings without changing files",
    )
    tasks_parser.add_argument(
        "--plan",
        default=".ai/AUTONOMOUS_PLAN.md",
        help="path to the autonomous roadmap file",
    )
    tasks_parser.add_argument(
        "--next",
        action="store_true",
        help="print only the next eligible TODO task",
    )

    lint_parser = subparsers.add_parser(
        "lint-plan",
        help="check roadmap task block structure without changing files",
    )
    lint_parser.add_argument(
        "--plan",
        default=".ai/AUTONOMOUS_PLAN.md",
        help="path to the autonomous roadmap file",
    )

    report_parser = subparsers.add_parser(
        "report",
        help="print a read-only dry-run repository report",
    )
    report_parser.add_argument(
        "--plan",
        default=".ai/AUTONOMOUS_PLAN.md",
        help="path to the autonomous roadmap file",
    )
    report_parser.add_argument(
        "--state",
        default=".ai/AUTONOMOUS_STATE.md",
        help="path to the autonomous state file",
    )
    report_parser.add_argument(
        "--policy",
        default=".forge/policy.md",
        help="path to the repository policy file",
    )

    policy_parser = subparsers.add_parser(
        "policy",
        help="parse repository policy sections without changing files",
    )
    policy_parser.add_argument(
        "--policy",
        default=".forge/policy.md",
        help="path to the repository policy file",
    )

    run_summary_parser = subparsers.add_parser(
        "run-summary",
        help="preview a local run summary without writing files",
    )
    run_summary_parser.add_argument(
        "--plan",
        default=".ai/AUTONOMOUS_PLAN.md",
        help="path to the autonomous roadmap file",
    )
    run_summary_parser.add_argument(
        "--policy",
        default=".forge/policy.md",
        help="path to the repository policy file",
    )
    run_summary_parser.add_argument(
        "--timestamp",
        default=None,
        help="optional ISO-8601 timestamp to make preview output deterministic",
    )

    inventory_parser = subparsers.add_parser(
        "inventory",
        help="print read-only repository health inventory signals",
    )
    inventory_parser.add_argument(
        "--root",
        default=".",
        help="repository root to inspect for file-presence signals",
    )

    drift_parser = subparsers.add_parser(
        "drift",
        help="detect consistency drift between metadata files and the repository",
    )
    drift_parser.add_argument(
        "--plan",
        default=".ai/AUTONOMOUS_PLAN.md",
        help="path to the autonomous roadmap file",
    )
    drift_parser.add_argument(
        "--state",
        default=".ai/AUTONOMOUS_STATE.md",
        help="path to the autonomous state file",
    )
    drift_parser.add_argument(
        "--changelog",
        default=".ai/AUTONOMOUS_CHANGELOG.md",
        help="path to the autonomous changelog file",
    )
    drift_parser.add_argument(
        "--policy",
        default=".forge/policy.md",
        help="path to the repository policy file",
    )
    drift_parser.add_argument(
        "--root",
        default=".",
        help="repository root to check policy path existence",
    )

    pause_parser = subparsers.add_parser(
        "pause",
        help="capture session context for later handoff",
    )
    pause_parser.add_argument(
        "--root",
        default=".",
        help="repository root for git state capture and session storage",
    )
    pause_parser.add_argument(
        "--working-on",
        default="",
        help="what you were working on",
    )
    pause_parser.add_argument(
        "--tried",
        default="",
        help="what you tried so far",
    )
    pause_parser.add_argument(
        "--stuck-on",
        default="",
        help="where you got stuck",
    )
    pause_parser.add_argument(
        "--half-finished",
        default="",
        help="what is half-finished",
    )
    pause_parser.add_argument(
        "--next-steps",
        default="",
        help="what to do next when resuming",
    )
    pause_parser.add_argument(
        "--notes",
        default="",
        help="any additional notes",
    )
    pause_parser.add_argument(
        "--timestamp",
        default=None,
        help="optional ISO-8601 timestamp for deterministic output",
    )

    resume_parser = subparsers.add_parser(
        "resume",
        help="replay the most recent session context as a briefing",
    )
    resume_parser.add_argument(
        "--root",
        default=".",
        help="repository root to find session files",
    )

    context_parser = subparsers.add_parser(
        "context",
        help="generate a comprehensive project context briefing",
    )
    context_parser.add_argument(
        "--root",
        default=".",
        help="repository root to inspect",
    )

    init_parser = subparsers.add_parser(
        "init",
        help="scaffold forge metadata into a repository",
    )
    init_parser.add_argument(
        "--root",
        default=".",
        help="repository root to initialize",
    )
    init_parser.add_argument(
        "--name",
        default=None,
        help="project name (defaults to directory name)",
    )

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
        "--timestamp",
        default=None,
        help="optional ISO-8601 timestamp for deterministic output",
    )

    sync_parser = subparsers.add_parser(
        "sync",
        help="sync AUTO tasks to Forgejo issues (one-way: plan -> Forgejo)",
    )
    sync_parser.add_argument(
        "--root",
        default=".",
        help="repository root",
    )
    sync_parser.add_argument(
        "--plan",
        default=None,
        help="path to the autonomous roadmap file",
    )
    sync_parser.add_argument(
        "--repo",
        default=None,
        help="Forgejo owner/repo (auto-detected from git remote)",
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be synced without making API calls",
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
        help="full autonomous pipeline: run -> commit -> sync",
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
        "--sync",
        action="store_true",
        help="sync to Forgejo after commit (opt-in)",
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
        "--timestamp",
        default=None,
        help="optional ISO-8601 timestamp for deterministic output",
    )

    mark_parser = subparsers.add_parser(
        "mark",
        help="update a task's status in the plan file",
    )
    mark_parser.add_argument(
        "task_id",
        help="task ID (e.g. AUTO-001)",
    )
    mark_parser.add_argument(
        "new_status",
        help="new status (TODO, DONE, BLOCKED)",
    )
    mark_parser.add_argument(
        "--plan",
        default=None,
        help="path to the autonomous roadmap file",
    )

    status_parser = subparsers.add_parser(
        "status",
        help="quick at-a-glance forge status",
    )
    status_parser.add_argument(
        "--root",
        default=".",
        help="repository root",
    )
    status_parser.add_argument(
        "--plan",
        default=None,
        help="path to the autonomous roadmap file",
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
    return parser


def _format_task(task) -> str:
    return f"{task.task_id} [{task.priority}/{task.status}] {task.title}"


def _format_policy(policy: RepositoryPolicy) -> str:
    return "\n".join(
        [
            "Repository policy summary",
            "Mode: read-only",
            f"Allowed paths: {len(policy.allowed_paths)}",
            f"Prohibited paths: {len(policy.prohibited_paths)}",
            f"Human approval required: {len(policy.approval_required)}",
            f"Validation expectations: {len(policy.validation_expectations)}",
        ]
    )


def _print_tasks(plan_path: Path, *, next_only: bool = False) -> int:
    try:
        tasks = parse_plan_tasks(plan_path.read_text(encoding="utf-8"))
        selected_task = select_eligible_task(tasks) if next_only else None
    except FileNotFoundError:
        print(f"Plan file not found: {plan_path}")
        return 2
    except (PlanParseError, PlanSelectionError) as exc:
        print(f"Plan error: {exc}")
        return 2

    if next_only:
        if selected_task is None:
            print("No eligible TODO task found.")
        else:
            print(_format_task(selected_task))
        return 0

    if not tasks:
        print("No autonomous tasks found.")
        return 0

    for task in tasks:
        print(_format_task(task))

    return 0


def _print_lint_plan(plan_path: Path) -> int:
    try:
        diagnostics = lint_plan_structure(plan_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"Plan file not found: {plan_path}")
        return 2

    if not diagnostics:
        print("Plan lint: ok")
        return 0

    print("Plan lint: failed")
    for diagnostic in diagnostics:
        print(f"line {diagnostic.line_number}: {diagnostic.message}")
    return 2


def _print_report(plan_path: Path, state_path: Path, policy_path: Path) -> int:
    try:
        print(read_repository_report(plan_path, state_path, policy_path))
    except FileNotFoundError:
        print(f"Plan file not found: {plan_path}")
        return 2
    except (PlanParseError, PlanSelectionError) as exc:
        print(f"Plan error: {exc}")
        return 2
    return 0


def _print_policy(policy_path: Path) -> int:
    try:
        policy = parse_repository_policy(policy_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"Policy file not found: {policy_path}")
        return 2
    except PolicyParseError as exc:
        print(f"Policy error: {exc}")
        return 2

    print(_format_policy(policy))
    return 0


def _print_run_summary(plan_path: Path, policy_path: Path, timestamp: str | None) -> int:
    try:
        print(read_run_summary_preview(plan_path, policy_path, timestamp=timestamp))
    except FileNotFoundError:
        print(f"Plan file not found: {plan_path}")
        return 2
    except (PlanParseError, PlanSelectionError) as exc:
        print(f"Plan error: {exc}")
        return 2
    return 0


def _print_inventory(root_path: Path) -> int:
    print(build_repository_inventory(root_path))
    return 0


def _print_drift(
    plan_path: Path,
    state_path: Path,
    changelog_path: Path,
    policy_path: Path,
    root_path: Path,
) -> int:
    try:
        print(
            read_drift_report(plan_path, state_path, changelog_path, policy_path, root_path)
        )
    except FileNotFoundError:
        print(f"Plan file not found: {plan_path}")
        return 2
    except (PlanParseError, PlanSelectionError) as exc:
        print(f"Plan error: {exc}")
        return 2
    return 0


def _run_pause(
    root_path: Path,
    *,
    working_on: str,
    tried: str,
    stuck_on: str,
    half_finished: str,
    next_steps: str,
    notes: str,
    timestamp: str | None,
) -> int:
    git = capture_git_snapshot(root_path)
    ctx = build_session_snapshot(
        git,
        working_on=working_on,
        tried=tried,
        stuck_on=stuck_on,
        half_finished=half_finished,
        next_steps=next_steps,
        notes=notes,
        timestamp=timestamp,
    )
    path = save_session(ctx, root_path)
    print(f"Session saved: {path}")
    return 0


def _run_resume(root_path: Path) -> int:
    ctx = load_latest_session(root_path)
    if ctx is None:
        print("No session found.")
        return 0
    print(format_resume_briefing(ctx))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the Forge CLI.

    Returns an exit code. When called as a console script, wraps with
    sys.exit via the ``_entry_point`` wrapper.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        from autonomous_forge import __version__

        print(f"forge {__version__}")
        return 0

    if args.command == "tasks":
        return _print_tasks(Path(args.plan), next_only=args.next)

    if args.command == "lint-plan":
        return _print_lint_plan(Path(args.plan))

    if args.command == "report":
        return _print_report(Path(args.plan), Path(args.state), Path(args.policy))

    if args.command == "policy":
        return _print_policy(Path(args.policy))

    if args.command == "run-summary":
        return _print_run_summary(Path(args.plan), Path(args.policy), args.timestamp)

    if args.command == "inventory":
        return _print_inventory(Path(args.root))

    if args.command == "drift":
        return _print_drift(
            Path(args.plan),
            Path(args.state),
            Path(args.changelog),
            Path(args.policy),
            Path(args.root),
        )

    if args.command == "pause":
        return _run_pause(
            Path(args.root),
            working_on=args.working_on,
            tried=args.tried,
            stuck_on=args.stuck_on,
            half_finished=args.half_finished,
            next_steps=args.next_steps,
            notes=args.notes,
            timestamp=args.timestamp,
        )

    if args.command == "resume":
        return _run_resume(Path(args.root))

    if args.command == "context":
        print(build_project_context(Path(args.root)))
        return 0

    if args.command == "init":
        from datetime import datetime, timezone

        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        result = init_forge(Path(args.root), project_name=args.name, date=date)
        print(format_init_result(result))
        return 0

    if args.command == "run":
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
            )
        except FileNotFoundError as exc:
            print(f"File not found: {exc}")
            return 2
        print(format_run_outcome(outcome))
        if not args.no_save:
            path = save_run_outcome(outcome, root)
            print(f"\nRun saved: {path}")
        return 1 if outcome.blocked else 0

    if args.command == "sync":
        root = Path(args.root)
        plan_path = Path(args.plan) if args.plan else None
        try:
            result = execute_sync(
                root,
                plan_path=plan_path,
                dry_run=args.dry_run,
                repo_override=args.repo,
            )
        except FileNotFoundError as exc:
            print(f"File not found: {exc}")
            return 2
        print(format_sync_result(result))
        return 1 if result.errors else 0

    if args.command == "pipeline":
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
                sync=args.sync,
                commit_message=args.pipeline_message,
                dry_run=args.dry_run,
                timestamp=args.timestamp,
            )
        except FileNotFoundError as exc:
            print(f"File not found: {exc}")
            return 2
        print(format_pipeline_result(result))
        if result.run_outcome and result.run_outcome.blocked:
            return 1
        if result.commit_result and not result.commit_result.committed and args.commit:
            return 1
        return 0

    if args.command == "log":
        entries = list_runs(Path(args.root), limit=args.limit)
        print(format_run_log(entries, verbose=args.verbose))
        return 0

    if args.command == "commit":
        root = Path(args.root)
        plan_path = Path(args.plan) if args.plan else None
        policy_path = Path(args.policy) if args.policy else None
        if args.check_only:
            pf = run_pre_flight(
                root, plan_path=plan_path, policy_path=policy_path,
                validate=not args.no_validate,
                validate_command=args.commit_cmd,
            )
            print(format_pre_flight(pf))
            return 0 if pf.safe else 1
        result = execute_commit(
            root, message=args.message,
            plan_path=plan_path, policy_path=policy_path,
            validate=not args.no_validate,
            validate_command=args.commit_cmd,
        )
        print(format_commit_result(result))
        return 0 if result.committed else 1

    if args.command == "mark":
        plan_path = Path(args.plan) if args.plan else None
        result = mark_task_status(args.task_id, args.new_status, plan_path)
        print(format_mark_result(result))
        return 0 if result.updated else 1

    if args.command == "status":
        root = Path(args.root)
        plan_path = Path(args.plan) if args.plan else None
        print(get_status(root, plan_path=plan_path))
        return 0

    if args.command == "diff-check":
        root = Path(args.root)
        policy_path = Path(args.policy) if args.policy else None
        print(read_diff_report(root, policy_path=policy_path, staged_only=args.staged))
        return 0

    if args.command == "validate":
        root = Path(args.root)
        policy_path = Path(args.policy) if args.policy else None
        result = run_validation(
            root, command=args.validate_cmd,
            policy_path=policy_path, timeout_seconds=args.timeout,
        )
        print(format_validation_result(result))
        return 0 if result.passed else 1

    parser.print_help()
    return 0


def _entry_point() -> None:
    """Console script entry point — wraps main() with sys.exit()."""
    import sys

    sys.exit(main())
