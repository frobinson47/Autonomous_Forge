"""CLI command for syncing AUTO tasks to Forgejo issues: sync."""

from __future__ import annotations

import argparse
from pathlib import Path

from autonomous_forge.sync import execute_sync, format_sync_result
from autonomous_forge.sync_orphans import (
    execute_import_orphans,
    execute_orphan_report,
    format_import_result,
    format_orphan_report,
)


def add_sync_parsers(subparsers: argparse._SubParsersAction) -> None:
    """Add the sync subcommand parser."""
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
