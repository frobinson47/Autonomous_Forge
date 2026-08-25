"""CLI commands for session/workflow management: pause, resume, context, init, doctor."""

from __future__ import annotations

import argparse
from pathlib import Path

from autonomous_forge.context import build_project_context
from autonomous_forge.doctor import format_doctor_report, run_doctor
from autonomous_forge.init import format_init_result, init_forge
from autonomous_forge.session import (
    build_session_snapshot,
    capture_git_snapshot,
    format_multi_resume_briefing,
    format_resume_briefing,
    load_latest_session,
    load_sessions_for_roots,
    save_session,
)


def add_session_parsers(subparsers: argparse._SubParsersAction) -> None:
    """Add the pause/resume/context/init/doctor subcommand parsers."""
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
