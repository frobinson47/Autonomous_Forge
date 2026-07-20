"""Tests for the forge watch periodic check loop."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from autonomous_forge.check import CheckResult
from autonomous_forge.watch import run_watch


def _passing_result() -> CheckResult:
    return CheckResult(
        lint_ok=True, lint_diagnostics=(),
        drift_ok=True, drift_signals=(),
        diff_ok=True, diff_violations=(),
        validation_ok=True, validation_output="",
        all_passed=True,
    )


def _failing_result() -> CheckResult:
    return CheckResult(
        lint_ok=False, lint_diagnostics=("line 1: bad",),
        drift_ok=True, drift_signals=(),
        diff_ok=True, diff_violations=(),
        validation_ok=None, validation_output="",
        all_passed=False,
    )


class TestRunWatch:
    @patch("autonomous_forge.watch.execute_check")
    def test_once_returns_pass_exit_code(self, mock_check, tmp_path: Path):
        mock_check.return_value = _passing_result()
        sleep_calls = []
        prints = []

        code = run_watch(
            tmp_path, once=True,
            sleep_fn=sleep_calls.append, print_fn=prints.append,
        )

        assert code == 0
        assert mock_check.call_count == 1
        assert sleep_calls == []
        assert "[cycle 1]" in prints[0]

    @patch("autonomous_forge.watch.execute_check")
    def test_once_returns_fail_exit_code(self, mock_check, tmp_path: Path):
        mock_check.return_value = _failing_result()

        code = run_watch(tmp_path, once=True, sleep_fn=lambda s: None, print_fn=lambda s: None)

        assert code == 1

    @patch("autonomous_forge.watch.execute_check")
    def test_max_cycles_bounds_the_loop(self, mock_check, tmp_path: Path):
        mock_check.return_value = _passing_result()
        sleep_calls = []
        prints = []

        code = run_watch(
            tmp_path, interval=42, max_cycles=3,
            sleep_fn=sleep_calls.append, print_fn=prints.append,
        )

        assert code == 0
        assert mock_check.call_count == 3
        assert len(prints) == 3
        assert "[cycle 3]" in prints[-1]
        # sleeps between cycles only — no sleep after the final (3rd) cycle
        assert sleep_calls == [42, 42]

    @patch("autonomous_forge.watch.execute_check")
    def test_keyboard_interrupt_exits_cleanly_with_zero(self, mock_check, tmp_path: Path):
        mock_check.return_value = _failing_result()  # would be exit 1 if not interrupted

        def _raise_interrupt(seconds):
            raise KeyboardInterrupt

        code = run_watch(
            tmp_path, interval=5,
            sleep_fn=_raise_interrupt, print_fn=lambda s: None,
        )

        assert code == 0

    @patch("autonomous_forge.watch.execute_check")
    def test_passes_through_check_kwargs(self, mock_check, tmp_path: Path):
        mock_check.return_value = _passing_result()

        run_watch(
            tmp_path,
            validate=False,
            validate_command="echo hi",
            timeout=15,
            once=True,
            sleep_fn=lambda s: None,
            print_fn=lambda s: None,
        )

        _, kwargs = mock_check.call_args
        assert kwargs["validate"] is False
        assert kwargs["validate_command"] == "echo hi"
        assert kwargs["timeout"] == 15


class TestWatchCLI:
    @patch("autonomous_forge.cli.run_watch")
    def test_watch_once_cli(self, mock_run_watch, tmp_path: Path):
        from autonomous_forge.cli import main

        mock_run_watch.return_value = 0
        code = main(["watch", "--root", str(tmp_path), "--once"])

        assert code == 0
        _, kwargs = mock_run_watch.call_args
        assert kwargs["once"] is True

    @patch("autonomous_forge.cli.run_watch")
    def test_watch_interval_passed_through(self, mock_run_watch, tmp_path: Path):
        from autonomous_forge.cli import main

        mock_run_watch.return_value = 1
        code = main(["watch", "--root", str(tmp_path), "--once", "--interval", "60"])

        assert code == 1
        _, kwargs = mock_run_watch.call_args
        assert kwargs["interval"] == 60
