"""Tests for forge status — quick at-a-glance view."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from autonomous_forge.status import get_status


PLAN = """\
# Roadmap

## Roadmap v1

### AUTO-001 — Build widget
Priority: P1
Status: TODO

Goal: Build a widget.
Why it matters: Yes.
Scope: Small.
Expected files or areas: src/
Acceptance criteria: Built.
Validation: Tests.
Risks or assumptions: None.
Notes: None.

### AUTO-002 — Paint widget
Priority: P2
Status: DONE

Goal: Paint it.
Why it matters: Yes.
Scope: Small.
Expected files or areas: src/
Acceptance criteria: Painted.
Validation: Tests.
Risks or assumptions: None.
Notes: None.
"""


def _setup(tmp_path: Path, plan: str = PLAN):
    (tmp_path / ".ai").mkdir()
    (tmp_path / ".ai/AUTONOMOUS_PLAN.md").write_text(plan, encoding="utf-8")
    (tmp_path / ".forge").mkdir()
    (tmp_path / ".forge/policy.md").write_text("# Policy\n", encoding="utf-8")


class TestGetStatus:
    @patch("autonomous_forge.status._git_branch", return_value="main")
    @patch("autonomous_forge.status._git_dirty_count", return_value=3)
    def test_basic_status(self, mock_dirty, mock_branch, tmp_path):
        _setup(tmp_path)
        output = get_status(root=tmp_path)
        assert "Branch: main" in output
        assert "Dirty: 3" in output
        assert "1 TODO" in output
        assert "1 DONE" in output
        assert "AUTO-001" in output
        assert "Policy: present" in output

    @patch("autonomous_forge.status._git_branch", return_value="main")
    @patch("autonomous_forge.status._git_dirty_count", return_value=0)
    def test_no_plan(self, mock_dirty, mock_branch, tmp_path):
        output = get_status(root=tmp_path)
        assert "not found" in output

    @patch("autonomous_forge.status._git_branch", return_value="feature")
    @patch("autonomous_forge.status._git_dirty_count", return_value=0)
    def test_no_policy(self, mock_dirty, mock_branch, tmp_path):
        _setup(tmp_path)
        (tmp_path / ".forge" / "policy.md").unlink()
        output = get_status(root=tmp_path)
        assert "Policy: missing" in output

    @patch("autonomous_forge.status._git_branch", return_value="main")
    @patch("autonomous_forge.status._git_dirty_count", return_value=0)
    def test_with_run_history(self, mock_dirty, mock_branch, tmp_path):
        _setup(tmp_path)
        runs = tmp_path / ".forge" / "runs"
        runs.mkdir()
        (runs / "run-2026-07-09T14-00-00.md").write_text("# Run\n", encoding="utf-8")
        output = get_status(root=tmp_path)
        assert "Last run:" in output
        assert "2026-07-09" in output

    @patch("autonomous_forge.status._git_branch", return_value="main")
    @patch("autonomous_forge.status._git_dirty_count", return_value=0)
    def test_all_done(self, mock_dirty, mock_branch, tmp_path):
        done_plan = PLAN.replace("Status: TODO", "Status: DONE")
        _setup(tmp_path, plan=done_plan)
        output = get_status(root=tmp_path)
        assert "Next: none" in output


class TestStatusCLI:
    @patch("autonomous_forge.status._git_branch", return_value="main")
    @patch("autonomous_forge.status._git_dirty_count", return_value=0)
    def test_status_cli(self, mock_dirty, mock_branch, tmp_path, capsys):
        _setup(tmp_path)
        from autonomous_forge.cli import main

        code = main(["status", "--root", str(tmp_path)])
        captured = capsys.readouterr()
        assert code == 0
        assert "Branch:" in captured.out
