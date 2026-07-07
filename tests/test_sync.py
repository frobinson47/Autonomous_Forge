"""Tests for the Forgejo sync module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from autonomous_forge.sync import (
    ForgejoClient,
    SyncAction,
    SyncResult,
    _detect_forgejo_repo,
    _find_issue_for_task,
    _labels_for_task,
    _task_issue_title,
    _detect_roadmap_version,
    _extract_task_block,
    execute_sync,
    format_sync_result,
)
from autonomous_forge.plan import PlanTask


SYNC_PLAN = """\
# Roadmap

## Roadmap v1

### AUTO-001 — Build the widget
Priority: P1
Status: DONE

Goal: Build a widget.

### AUTO-002 — Test the widget
Priority: P2
Status: TODO

Goal: Write tests for the widget.

## Roadmap v2

### AUTO-003 — Polish the widget
Priority: P1
Status: TODO

Goal: Add polish.
"""


def _make_task(task_id="AUTO-001", title="Build the widget", priority="P1", status="DONE"):
    return PlanTask(task_id=task_id, title=title, priority=priority, status=status, line_number=1)


class TestHelpers:
    def test_task_issue_title(self):
        task = _make_task()
        assert _task_issue_title(task) == "[AUTO-001] Build the widget"

    def test_find_issue_for_task(self):
        issues = [
            {"title": "[AUTO-001] Build the widget", "number": 1},
            {"title": "[AUTO-002] Test the widget", "number": 2},
        ]
        assert _find_issue_for_task("AUTO-001", issues)["number"] == 1
        assert _find_issue_for_task("AUTO-003", issues) is None

    def test_labels_for_task(self):
        label_map = {
            "status:todo": 10,
            "status:done": 11,
            "priority:high": 20,
            "priority:medium": 21,
            "forge-sync": 30,
        }
        task = _make_task(status="DONE", priority="P1")
        ids = _labels_for_task(task, label_map)
        assert 11 in ids  # status:done
        assert 20 in ids  # priority:high
        assert 30 in ids  # forge-sync

    def test_detect_roadmap_version(self):
        assert _detect_roadmap_version(_make_task("AUTO-001"), SYNC_PLAN) == "Roadmap v1"
        assert _detect_roadmap_version(_make_task("AUTO-003"), SYNC_PLAN) == "Roadmap v2"

    def test_extract_task_block(self):
        block = _extract_task_block("AUTO-002", SYNC_PLAN)
        assert "Write tests" in block
        assert "AUTO-001" not in block

    def test_detect_forgejo_repo(self, tmp_path: Path):
        with patch("autonomous_forge.sync.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="https://forgejo.familytechlab.com/frank/Autonomous-Forge.git\n"
            )
            result = _detect_forgejo_repo(tmp_path)
            assert result == "frank/Autonomous-Forge"

    def test_detect_forgejo_repo_non_forgejo(self, tmp_path: Path):
        with patch("autonomous_forge.sync.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="https://github.com/foo/bar.git\n")
            result = _detect_forgejo_repo(tmp_path)
            assert result is None


class TestExecuteSync:
    def _setup_plan(self, tmp_path: Path):
        ai_dir = tmp_path / ".ai"
        ai_dir.mkdir()
        (ai_dir / "AUTONOMOUS_PLAN.md").write_text(SYNC_PLAN, encoding="utf-8")

    def test_dry_run(self, tmp_path: Path):
        self._setup_plan(tmp_path)
        result = execute_sync(
            root=tmp_path,
            dry_run=True,
            repo_override="frank/Test",
            token_override="fake-token",
        )
        assert len(result.actions) == 3
        assert all(a.action.startswith("would-") for a in result.actions)
        assert result.repo == "frank/Test"
        assert not result.errors

    def test_no_repo_detected(self, tmp_path: Path):
        self._setup_plan(tmp_path)
        with patch("autonomous_forge.sync._detect_forgejo_repo", return_value=None):
            result = execute_sync(root=tmp_path)
        assert result.errors
        assert "Could not detect" in result.errors[0]

    def test_no_token(self, tmp_path: Path):
        self._setup_plan(tmp_path)
        with patch("autonomous_forge.sync._load_token", return_value=None):
            result = execute_sync(
                root=tmp_path,
                repo_override="frank/Test",
            )
        assert result.errors
        assert "token" in result.errors[0].lower()


class TestFormatSyncResult:
    def test_format_dry_run(self):
        result = SyncResult(
            actions=(
                SyncAction("AUTO-001", "would-sync", detail="Build the widget [P1/DONE]"),
                SyncAction("AUTO-002", "would-create", detail="Test the widget [P2/TODO]"),
            ),
            repo="frank/Test",
        )
        text = format_sync_result(result)
        assert "frank/Test" in text
        assert "Tasks synced: 2" in text

    def test_format_with_created(self):
        result = SyncResult(
            actions=(
                SyncAction("AUTO-001", "created", issue_number=1, detail="Build the widget"),
                SyncAction("AUTO-002", "up-to-date", issue_number=2, detail="Test the widget"),
            ),
            repo="frank/Test",
        )
        text = format_sync_result(result)
        assert "Created: 1" in text
        assert "Up to date: 1" in text
        assert "#1" in text

    def test_format_with_errors(self):
        result = SyncResult(
            actions=(),
            repo="frank/Test",
            errors=("No token found.",),
        )
        text = format_sync_result(result)
        assert "ERROR" in text


class TestSyncCLI:
    def test_sync_dry_run_cli(self, tmp_path: Path, capsys):
        ai_dir = tmp_path / ".ai"
        ai_dir.mkdir()
        (ai_dir / "AUTONOMOUS_PLAN.md").write_text(SYNC_PLAN, encoding="utf-8")

        from autonomous_forge.cli import main

        code = main([
            "sync",
            "--root", str(tmp_path),
            "--plan", str(ai_dir / "AUTONOMOUS_PLAN.md"),
            "--repo", "frank/Test",
            "--dry-run",
        ])
        captured = capsys.readouterr()
        assert code == 0
        assert "frank/Test" in captured.out
        assert "AUTO-001" in captured.out
