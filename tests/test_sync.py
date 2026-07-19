"""Tests for the Forgejo sync module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from autonomous_forge.sync import (
    ForgejoClient,
    OrphanIssue,
    OrphanReport,
    SyncAction,
    SyncResult,
    _detect_forgejo_repo,
    _find_issue_for_task,
    _labels_for_task,
    _task_issue_title,
    _detect_roadmap_version,
    _extract_task_block,
    execute_orphan_report,
    execute_sync,
    find_orphan_issues,
    format_orphan_report,
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

    def test_find_issue_for_task_matches_legacy_unbracketed_title(self):
        # Repos with issues filed manually before forge-sync existed use
        # "AUTO-001: Title" (no brackets) — sync must recognize these as the
        # same task, or it creates a duplicate issue every run.
        issues = [{"title": "AUTO-001: Build the widget", "number": 7}]
        assert _find_issue_for_task("AUTO-001", issues)["number"] == 7

    def test_find_issue_for_task_matches_bracketed_among_mixed_titles(self):
        issues = [
            {"title": "AUTO-002: Test the widget", "number": 7},
            {"title": "[AUTO-001] Build the widget", "number": 12},
        ]
        assert _find_issue_for_task("AUTO-001", issues)["number"] == 12

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


class TestFindOrphanIssues:
    def test_finds_issue_with_no_auto_id(self):
        tasks = [_make_task("AUTO-001")]
        issues = [{"number": 5, "state": "open", "title": "Fix the login bug"}]
        orphans = find_orphan_issues(issues, tasks)
        assert len(orphans) == 1
        assert orphans[0]["number"] == 5

    def test_finds_issue_referencing_removed_task(self):
        tasks = [_make_task("AUTO-001")]
        issues = [{"number": 6, "state": "open", "title": "[AUTO-099] Old removed task"}]
        orphans = find_orphan_issues(issues, tasks)
        assert len(orphans) == 1

    def test_excludes_issue_matching_current_task(self):
        tasks = [_make_task("AUTO-001")]
        issues = [{"number": 1, "state": "open", "title": "[AUTO-001] Build the widget"}]
        assert find_orphan_issues(issues, tasks) == []

    def test_excludes_closed_issues(self):
        tasks = [_make_task("AUTO-001")]
        issues = [{"number": 9, "state": "closed", "title": "Fix the login bug"}]
        assert find_orphan_issues(issues, tasks) == []

    def test_matches_unbracketed_auto_id(self):
        tasks = [_make_task("AUTO-001")]
        issues = [{"number": 2, "state": "open", "title": "AUTO-001: Build the widget"}]
        assert find_orphan_issues(issues, tasks) == []


class TestExecuteOrphanReport:
    def _setup_plan(self, tmp_path: Path):
        ai_dir = tmp_path / ".ai"
        ai_dir.mkdir()
        (ai_dir / "AUTONOMOUS_PLAN.md").write_text(SYNC_PLAN, encoding="utf-8")

    def test_no_repo_detected(self, tmp_path: Path):
        self._setup_plan(tmp_path)
        with patch("autonomous_forge.sync._detect_forgejo_repo", return_value=None):
            report = execute_orphan_report(root=tmp_path)
        assert report.errors
        assert "Could not detect" in report.errors[0]

    def test_no_token(self, tmp_path: Path):
        self._setup_plan(tmp_path)
        with patch("autonomous_forge.sync._load_token", return_value=None):
            report = execute_orphan_report(root=tmp_path, repo_override="frank/Test")
        assert report.errors
        assert "token" in report.errors[0].lower()

    def test_reports_orphans_and_makes_no_write_calls(self, tmp_path: Path):
        self._setup_plan(tmp_path)
        mock_client = MagicMock()
        mock_client.list_issues.return_value = [
            {"number": 5, "state": "open", "title": "Manually filed bug"},
            {"number": 1, "state": "open", "title": "[AUTO-001] Build the widget"},
        ]
        with patch("autonomous_forge.sync.ForgejoClient", return_value=mock_client):
            report = execute_orphan_report(
                root=tmp_path, repo_override="frank/Test", token_override="fake-token",
            )

        assert len(report.orphans) == 1
        assert report.orphans[0].number == 5
        mock_client.list_issues.assert_called_once_with(state="open")
        mock_client.create_issue.assert_not_called()
        mock_client.update_issue.assert_not_called()
        mock_client.add_comment.assert_not_called()

    def test_no_orphans(self, tmp_path: Path):
        self._setup_plan(tmp_path)
        mock_client = MagicMock()
        mock_client.list_issues.return_value = [
            {"number": 1, "state": "open", "title": "[AUTO-001] Build the widget"},
        ]
        with patch("autonomous_forge.sync.ForgejoClient", return_value=mock_client):
            report = execute_orphan_report(
                root=tmp_path, repo_override="frank/Test", token_override="fake-token",
            )
        assert report.orphans == ()


class TestFormatOrphanReport:
    def test_no_orphans(self):
        report = OrphanReport(orphans=(), repo="frank/Test")
        text = format_orphan_report(report)
        assert "No orphan issues" in text

    def test_with_orphans(self):
        report = OrphanReport(
            orphans=(OrphanIssue(number=5, title="Manually filed bug", url="https://x/5"),),
            repo="frank/Test",
        )
        text = format_orphan_report(report)
        assert "Orphan issues: 1" in text
        assert "#5" in text
        assert "Manually filed bug" in text

    def test_with_errors(self):
        report = OrphanReport(orphans=(), repo="frank/Test", errors=("No token found.",))
        text = format_orphan_report(report)
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

    def test_report_orphans_cli(self, tmp_path: Path, capsys):
        ai_dir = tmp_path / ".ai"
        ai_dir.mkdir()
        (ai_dir / "AUTONOMOUS_PLAN.md").write_text(SYNC_PLAN, encoding="utf-8")

        from autonomous_forge.cli import main

        mock_client = MagicMock()
        mock_client.list_issues.return_value = [
            {"number": 5, "state": "open", "title": "Manually filed bug"},
        ]
        with patch("autonomous_forge.sync.ForgejoClient", return_value=mock_client), \
             patch("autonomous_forge.sync._load_token", return_value="fake-token"):
            code = main([
                "sync",
                "--root", str(tmp_path),
                "--plan", str(ai_dir / "AUTONOMOUS_PLAN.md"),
                "--repo", "frank/Test",
                "--report-orphans",
            ])
        captured = capsys.readouterr()
        assert code == 0
        assert "#5" in captured.out
        mock_client.create_issue.assert_not_called()
