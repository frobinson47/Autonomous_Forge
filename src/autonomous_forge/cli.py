"""Command-line interface for Autonomous Forge."""

from __future__ import annotations

import argparse
from pathlib import Path

from autonomous_forge.plan import (
    PlanParseError,
    PlanSelectionError,
    parse_plan_tasks,
    select_eligible_task,
)
from autonomous_forge.report import read_repository_report


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
    return parser


def _format_task(task) -> str:
    return f"{task.task_id} [{task.priority}/{task.status}] {task.title}"


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


def _print_report(plan_path: Path, state_path: Path) -> int:
    try:
        print(read_repository_report(plan_path, state_path))
    except FileNotFoundError:
        print(f"Plan file not found: {plan_path}")
        return 2
    except (PlanParseError, PlanSelectionError) as exc:
        print(f"Plan error: {exc}")
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the Forge CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        from autonomous_forge import __version__

        print(f"forge {__version__}")
        return 0

    if args.command == "tasks":
        return _print_tasks(Path(args.plan), next_only=args.next)

    if args.command == "report":
        return _print_report(Path(args.plan), Path(args.state))

    parser.print_help()
    return 0
