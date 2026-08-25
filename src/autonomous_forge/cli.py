"""Command-line interface for Autonomous Forge."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

from autonomous_forge.cli_plan import (
    _cmd_drift,
    _cmd_export,
    _cmd_inventory,
    _cmd_lint_plan,
    _cmd_mark,
    _cmd_metrics,
    _cmd_plan,
    _cmd_policy,
    _cmd_report,
    _cmd_run_summary,
    _cmd_status,
    _cmd_tasks,
    add_plan_parsers,
)
from autonomous_forge.cli_run import (
    _cmd_approve,
    _cmd_check,
    _cmd_commit,
    _cmd_diff_check,
    _cmd_log,
    _cmd_pipeline,
    _cmd_push,
    _cmd_revert,
    _cmd_run,
    _cmd_validate,
    _cmd_watch,
    add_run_parsers,
)
from autonomous_forge.cli_session import (
    _cmd_context,
    _cmd_doctor,
    _cmd_init,
    _cmd_pause,
    _cmd_resume,
    add_session_parsers,
)
from autonomous_forge.cli_sync import _cmd_sync, add_sync_parsers
from autonomous_forge.config import apply_config_defaults, load_config


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
    add_plan_parsers(subparsers)
    add_session_parsers(subparsers)
    add_run_parsers(subparsers)
    add_sync_parsers(subparsers)

    return parser


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
