"""Periodic forge check loop — foreground, read-only, no daemonization."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from autonomous_forge.check import execute_check, format_check_result


DEFAULT_INTERVAL_SECONDS = 300


def run_watch(
    root: Path = Path("."),
    plan_path: Path | None = None,
    policy_path: Path | None = None,
    validate: bool = True,
    validate_command: str | None = None,
    timeout: int = 300,
    interval: int = DEFAULT_INTERVAL_SECONDS,
    once: bool = False,
    max_cycles: int | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    print_fn: Callable[[str], None] = print,
) -> int:
    """Run `forge check` on a loop and return the last cycle's exit code.

    Foreground only — no daemonization, no PID files, no autonomous fixes.
    `--once` (or ``once=True``) runs a single cycle and returns immediately
    with that cycle's exit code. Otherwise loops until interrupted; a
    KeyboardInterrupt (Ctrl+C) exits cleanly with code 0 regardless of the
    last check's outcome — interruption is not itself a failure.
    ``max_cycles`` bounds the loop for testing; it is not exposed on the CLI.
    """
    cycle = 0
    last_exit_code = 0
    try:
        while True:
            cycle += 1
            result = execute_check(
                root,
                plan_path=plan_path,
                policy_path=policy_path,
                validate=validate,
                validate_command=validate_command,
                timeout=timeout,
            )
            report = format_check_result(result).replace("\n", "\n  ")
            print_fn(f"[cycle {cycle}] {report}")
            last_exit_code = 0 if result.all_passed else 1

            if once or (max_cycles is not None and cycle >= max_cycles):
                return last_exit_code

            sleep_fn(interval)
    except KeyboardInterrupt:
        return 0
