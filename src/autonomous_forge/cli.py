"""Command-line interface for Autonomous Forge."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

from autonomous_forge.approvals import format_approval_confirmation, record_approval
from autonomous_forge.check import execute_check, format_check_result
from autonomous_forge.commit import (
    execute_commit,
    format_commit_result,
    format_pre_flight,
    run_pre_flight,
)
from autonomous_forge.config import apply_config_defaults, load_config
from autonomous_forge.context import build_project_context
from autonomous_forge.diffcheck import read_diff_report
from autonomous_forge.doctor import format_doctor_report, run_doctor
from autonomous_forge.drift import read_drift_report
from autonomous_forge.export import export_state
from autonomous_forge.init import format_init_result, init_forge
from autonomous_forge.inventory import build_repository_inventory
from autonomous_forge.log import format_run_log, list_runs
from autonomous_forge.mark import format_mark_result, mark_task_status
from autonomous_forge.metrics import (
    compute_metrics,
    format_metrics,
    format_metrics_json,
)
from autonomous_forge.pipeline import execute_pipeline, format_pipeline_result
from autonomous_forge.plan import (
    PlanParseError,
    PlanSelectionError,
    lint_plan_structure,
    parse_plan_tasks,
    select_eligible_task,
)
from autonomous_forge.planadd import add_task, format_add_result
from autonomous_forge.policy import (
    PolicyParseError,
    RepositoryPolicy,
    parse_repository_policy,
)
from autonomous_forge.push import execute_push, format_push_result
from autonomous_forge.report import read_repository_report
from autonomous_forge.revert import execute_revert, format_revert_result
from autonomous_forge.run import execute_run, format_run_outcome, save_run_outcome
from autonomous_forge.run_summary import read_run_summary_preview
from autonomous_forge.session import (
    build_session_snapshot,
    capture_git_snapshot,
    format_multi_resume_briefing,
    format_resume_briefing,
    load_latest_session,
    load_sessions_for_roots,
    save_session,
)
from autonomous_forge.status import get_status
from autonomous_forge.sync import execute_sync, format_sync_result
from autonomous_forge.sync_orphans import (
    execute_import_orphans,
    execute_orphan_report,
    format_import_result,
    format_orphan_report,
)
from autonomous_forge.validate import format_validation_result, run_validation
from autonomous_forge.watch import run_watch


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
        default=None,
        help="path to the autonomous roadmap file (default: .ai/AUTONOMOUS_PLAN.md)",
    )
    tasks_parser.add_argument(
        "--next",
        action="store_true",
        help="print only the next eligible TODO task",
    )
    tasks_parser.add_argument(
        "--status",
        default=None,
        help="filter by status (TODO, DONE, BLOCKED, SKIPPED)",
    )
    tasks_parser.add_argument(
        "--priority",
        default=None,
        help="filter by priority (P0, P1, P2, P3)",
    )

    lint_parser = subparsers.add_parser(
        "lint-plan",
        help="check roadmap task block structure without changing files",
    )
    lint_parser.add_argument(
        "--plan",
        default=None,
        help="path to the autonomous roadmap file (default: .ai/AUTONOMOUS_PLAN.md)",
    )

    report_parser = subparsers.add_parser(
        "report",
        help="print a read-only dry-run repository report",
    )
    report_parser.add_argument(
        "--plan",
        default=None,
        help="path to the autonomous roadmap file (default: .ai/AUTONOMOUS_PLAN.md)",
    )
    report_parser.add_argument(
        "--state",
        default=".ai/AUTONOMOUS_STATE.md",
        help="path to the autonomous state file",
    )
    report_parser.add_argument(
        "--policy",
        default=None,
        help="path to the repository policy file (default: .forge/policy.md)",
    )

    policy_parser = subparsers.add_parser(
        "policy",
        help="parse repository policy sections without changing files",
    )
    policy_parser.add_argument(
        "--policy",
        default=None,
        help="path to the repository policy file (default: .forge/policy.md)",
    )

    run_summary_parser = subparsers.add_parser(
        "run-summary",
        help="preview a local run summary without writing files",
    )
    run_summary_parser.add_argument(
        "--plan",
        default=None,
        help="path to the autonomous roadmap file (default: .ai/AUTONOMOUS_PLAN.md)",
    )
    run_summary_parser.add_argument(
        "--policy",
        default=None,
        help="path to the repository policy file (default: .forge/policy.md)",
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
        default=None,
        help="path to the autonomous roadmap file (default: .ai/AUTONOMOUS_PLAN.md)",
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
        default=None,
        help="path to the repository policy file (default: .forge/policy.md)",
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
    resume_parser.add_argument(
        "--roots",
        default=None,
        help="comma-separated repo roots for a combined cross-repo briefing (overrides --root)",
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
        "--base-url",
        default=None,
        help=(
            "Forgejo instance base URL, e.g. https://forgejo.example.com "
            "(default: FORGEJO_BASE_URL env var, then .forge/config.toml's "
            "forgejo_base_url, then this project's own instance)"
        ),
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be synced without making API calls",
    )
    sync_parser.add_argument(
        "--report-orphans",
        action="store_true",
        help="read-only: list open Forgejo issues with no matching AUTO-### plan task",
    )
    sync_parser.add_argument(
        "--import-orphans",
        action="store_true",
        help="write AUTO-### plan stubs for current orphan Forgejo issues (see DEC-010)",
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

    plan_parser = subparsers.add_parser(
        "plan",
        help="plan management commands",
    )
    plan_subparsers = plan_parser.add_subparsers(dest="plan_action")
    plan_add_parser = plan_subparsers.add_parser(
        "add",
        help="add a new task to the plan",
    )
    plan_add_parser.add_argument(
        "--title",
        required=True,
        help="task title",
    )
    plan_add_parser.add_argument(
        "--goal",
        required=True,
        help="task goal",
    )
    plan_add_parser.add_argument(
        "--priority",
        default="P1",
        help="task priority (P0-P3, default: P1)",
    )
    plan_add_parser.add_argument(
        "--plan",
        default=None,
        help="path to the autonomous roadmap file",
    )
    plan_add_parser.add_argument(
        "--scope",
        default="",
        help="task scope",
    )
    plan_add_parser.add_argument(
        "--files",
        default="",
        help="expected files or areas",
    )
    plan_add_parser.add_argument(
        "--acceptance",
        default="",
        help="acceptance criteria",
    )
    plan_add_parser.add_argument(
        "--notes",
        default="",
        help="additional notes",
    )

    metrics_parser = subparsers.add_parser(
        "metrics",
        help="aggregate stats from run history",
    )
    metrics_parser.add_argument(
        "--root",
        default=".",
        help="repository root",
    )
    metrics_parser.add_argument(
        "--json",
        action="store_true",
        help="print metrics as JSON instead of the human-readable report",
    )

    export_parser = subparsers.add_parser(
        "export",
        help="export forge state as JSON",
    )
    export_parser.add_argument(
        "--root",
        default=".",
        help="repository root",
    )
    export_parser.add_argument(
        "--plan",
        default=None,
        help="path to the autonomous roadmap file",
    )
    export_parser.add_argument(
        "--runs",
        action="store_true",
        help="include run history in export",
    )
    export_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="max runs to include (default: 20)",
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

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="diagnose common environment issues before a run",
    )
    doctor_parser.add_argument(
        "--root",
        default=".",
        help="repository root",
    )
    doctor_parser.add_argument(
        "--plan",
        default=None,
        help="path to the autonomous roadmap file",
    )
    doctor_parser.add_argument(
        "--policy",
        default=None,
        help="path to the repository policy file",
    )
    doctor_parser.add_argument(
        "--repo",
        default=None,
        help="Forgejo owner/repo override (auto-detected from git remote if omitted)",
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


def _print_tasks(
    plan_path: Path,
    *,
    next_only: bool = False,
    status_filter: str | None = None,
    priority_filter: str | None = None,
) -> int:
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

    filtered = tasks
    if status_filter:
        filtered = [t for t in filtered if t.status == status_filter.upper()]
    if priority_filter:
        filtered = [t for t in filtered if t.priority == priority_filter.upper()]

    if not filtered:
        print("No matching tasks found.")
        return 0

    for task in filtered:
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


def _run_resume_multi(roots_arg: str) -> int:
    roots = [Path(r.strip()) for r in roots_arg.split(",") if r.strip()]
    sessions = load_sessions_for_roots(roots)
    print(format_multi_resume_briefing(sessions))
    return 0


def _cmd_tasks(args: argparse.Namespace) -> int:
    return _print_tasks(
        Path(args.plan or ".ai/AUTONOMOUS_PLAN.md"),
        next_only=args.next,
        status_filter=args.status,
        priority_filter=args.priority,
    )


def _cmd_lint_plan(args: argparse.Namespace) -> int:
    return _print_lint_plan(Path(args.plan or ".ai/AUTONOMOUS_PLAN.md"))


def _cmd_report(args: argparse.Namespace) -> int:
    return _print_report(
        Path(args.plan or ".ai/AUTONOMOUS_PLAN.md"),
        Path(args.state),
        Path(args.policy or ".forge/policy.md"),
    )


def _cmd_policy(args: argparse.Namespace) -> int:
    return _print_policy(Path(args.policy or ".forge/policy.md"))


def _cmd_run_summary(args: argparse.Namespace) -> int:
    return _print_run_summary(
        Path(args.plan or ".ai/AUTONOMOUS_PLAN.md"),
        Path(args.policy or ".forge/policy.md"),
        args.timestamp,
    )


def _cmd_inventory(args: argparse.Namespace) -> int:
    return _print_inventory(Path(args.root))


def _cmd_drift(args: argparse.Namespace) -> int:
    return _print_drift(
        Path(args.plan or ".ai/AUTONOMOUS_PLAN.md"),
        Path(args.state),
        Path(args.changelog),
        Path(args.policy or ".forge/policy.md"),
        Path(args.root),
    )


def _cmd_pause(args: argparse.Namespace) -> int:
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


def _cmd_resume(args: argparse.Namespace) -> int:
    if args.roots:
        return _run_resume_multi(args.roots)
    return _run_resume(Path(args.root))


def _cmd_context(args: argparse.Namespace) -> int:
    print(build_project_context(Path(args.root)))
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    from datetime import datetime, timezone

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    result = init_forge(Path(args.root), project_name=args.name, date=date)
    print(format_init_result(result))
    return 0


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


def _cmd_sync(args: argparse.Namespace) -> int:
    root = Path(args.root)
    plan_path = Path(args.plan) if args.plan else None
    if args.import_orphans:
        try:
            import_result = execute_import_orphans(
                root,
                plan_path=plan_path,
                repo_override=args.repo,
                base_url_override=args.base_url,
            )
        except FileNotFoundError as exc:
            print(f"File not found: {exc}")
            return 2
        print(format_import_result(import_result))
        return 1 if import_result.errors else 0
    if args.report_orphans:
        try:
            orphan_report = execute_orphan_report(
                root,
                plan_path=plan_path,
                repo_override=args.repo,
                base_url_override=args.base_url,
            )
        except FileNotFoundError as exc:
            print(f"File not found: {exc}")
            return 2
        print(format_orphan_report(orphan_report))
        return 1 if orphan_report.errors else 0
    try:
        result = execute_sync(
            root,
            plan_path=plan_path,
            dry_run=args.dry_run,
            repo_override=args.repo,
            base_url_override=args.base_url,
        )
    except FileNotFoundError as exc:
        print(f"File not found: {exc}")
        return 2
    print(format_sync_result(result))
    return 1 if result.errors else 0


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


def _cmd_mark(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan) if args.plan else None
    result = mark_task_status(args.task_id, args.new_status, plan_path)
    print(format_mark_result(result))
    return 0 if result.updated else 1


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


def _cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.root)
    plan_path = Path(args.plan) if args.plan else None
    print(get_status(root, plan_path=plan_path))
    return 0


def _cmd_plan(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.plan_action == "add":
        plan_path = Path(args.plan) if args.plan else None
        result = add_task(
            args.title,
            goal=args.goal,
            priority=args.priority,
            plan_path=plan_path,
            scope=args.scope,
            files=args.files,
            acceptance=args.acceptance,
            notes=args.notes,
        )
        print(format_add_result(result))
        return 0 if result.added else 1
    # `plan_parser` (the "plan" subcommand's own parser) is a local variable
    # inside build_parser(), not accessible here — previously this line
    # referenced it directly and raised NameError on `forge plan` with no
    # subcommand. Fall back to the top-level parser's help instead.
    parser.print_help()
    return 0


def _cmd_metrics(args: argparse.Namespace) -> int:
    m = compute_metrics(Path(args.root))
    print(format_metrics_json(m) if args.json else format_metrics(m))
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    root = Path(args.root)
    plan_path = Path(args.plan) if args.plan else None
    print(export_state(root, plan_path=plan_path, include_runs=args.runs, run_limit=args.limit))
    return 0


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


def _cmd_doctor(args: argparse.Namespace) -> int:
    root = Path(args.root)
    plan_path = Path(args.plan) if args.plan else None
    policy_path = Path(args.policy) if args.policy else None
    result = run_doctor(
        root,
        plan_path=plan_path,
        policy_path=policy_path,
        repo_override=args.repo,
    )
    print(format_doctor_report(result))
    return 0 if result.all_passed else 1


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


# Maps `args.command` to its handler. "plan" and "version" are special-cased
# in main() — "plan" needs the top-level parser for its help fallback, and
# "version" is checked before a command is even required.
_COMMAND_HANDLERS: dict[str, Callable[[argparse.Namespace], int]] = {
    "tasks": _cmd_tasks,
    "lint-plan": _cmd_lint_plan,
    "report": _cmd_report,
    "policy": _cmd_policy,
    "run-summary": _cmd_run_summary,
    "inventory": _cmd_inventory,
    "drift": _cmd_drift,
    "pause": _cmd_pause,
    "resume": _cmd_resume,
    "context": _cmd_context,
    "init": _cmd_init,
    "run": _cmd_run,
    "sync": _cmd_sync,
    "pipeline": _cmd_pipeline,
    "log": _cmd_log,
    "commit": _cmd_commit,
    "push": _cmd_push,
    "mark": _cmd_mark,
    "approve": _cmd_approve,
    "revert": _cmd_revert,
    "status": _cmd_status,
    "metrics": _cmd_metrics,
    "export": _cmd_export,
    "check": _cmd_check,
    "watch": _cmd_watch,
    "doctor": _cmd_doctor,
    "diff-check": _cmd_diff_check,
    "validate": _cmd_validate,
}


def main(argv: list[str] | None = None) -> int:
    """Run the Forge CLI.

    Returns an exit code. When called as a console script, wraps with
    sys.exit via the ``_entry_point`` wrapper.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_config(Path(getattr(args, "root", ".")))
    apply_config_defaults(args, config)

    if args.version:
        from autonomous_forge import __version__

        print(f"forge {__version__}")
        return 0

    if args.command == "plan":
        return _cmd_plan(args, parser)

    handler = _COMMAND_HANDLERS.get(args.command)
    if handler is not None:
        return handler(args)

    parser.print_help()
    return 0


def _entry_point() -> None:
    """Console script entry point — wraps main() with sys.exit()."""
    import sys

    sys.exit(main())
