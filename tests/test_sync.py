"""Tests for the Forgejo sync module (issue-matching / label / milestone reconciliation)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from autonomous_forge.plan import PlanTask
from autonomous_forge.sync import (
    SyncAction,
    SyncResult,
    _detect_roadmap_version,
    _extract_task_block,
    _find_issue_for_task,
    _labels_for_task,
    _task_issue_title,
    execute_sync,
    format_sync_result,
)

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

    def test_find_issue_for_task_prefers_lowest_number_when_duplicates_exist(self):
        # A leftover duplicate (e.g. from before this matching fix existed)
        # must not win just because the API listed it first (newest-first).
        issues = [
            {"title": "[AUTO-001] Build the widget", "number": 51},
            {"title": "AUTO-001: Build the widget", "number": 6},
        ]
        assert _find_issue_for_task("AUTO-001", issues)["number"] == 6

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

    def test_detect_roadmap_version_resets_on_other_section_heading(self):
        # A non-"Roadmap vN" section (e.g. "## Backlog") after a roadmap
        # section must NOT inherit that roadmap's milestone — regression
        # test for a bug where a task under "## Backlog" silently kept
        # getting synced into "Roadmap v1" because current_version was
        # never reset by any heading other than "## Roadmap vN".
        plan = SYNC_PLAN + """
## Backlog

### AUTO-004 — Someday maybe
Priority: P3
Status: TODO

Goal: Not scheduled yet.
"""
        assert _detect_roadmap_version(_make_task("AUTO-004"), plan) is None

    def test_extract_task_block(self):
        block = _extract_task_block("AUTO-002", SYNC_PLAN)
        assert "Write tests" in block
        assert "AUTO-001" not in block


class TestExecuteSync:
    def _setup_plan(self, tmp_path: Path):
        ai_dir = tmp_path / ".ai"
        ai_dir.mkdir()
        (ai_dir / "AUTONOMOUS_PLAN.md").write_text(SYNC_PLAN, encoding="utf-8")

    def test_dry_run(self, tmp_path: Path):
        self._setup_plan(tmp_path)
        with patch("autonomous_forge.sync.ForgejoClient.list_issues", return_value=[]):
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

    def test_dry_run_matches_existing_issue(self, tmp_path: Path):
        # A DONE task with a pre-existing issue must report "would-sync"
        # against that issue, not a status-derived guess.
        self._setup_plan(tmp_path)
        existing = [{"title": "[AUTO-001] Build the widget", "number": 9}]
        with patch("autonomous_forge.sync.ForgejoClient.list_issues", return_value=existing):
            result = execute_sync(
                root=tmp_path,
                dry_run=True,
                repo_override="frank/Test",
                token_override="fake-token",
            )
        action = next(a for a in result.actions if a.task_id == "AUTO-001")
        assert action.action == "would-sync"
        assert action.issue_number == 9

        action = next(a for a in result.actions if a.task_id == "AUTO-002")
        assert action.action == "would-create"
        assert action.issue_number is None

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

        # Must patch _load_token explicitly: without it, this test only
        # passed by accident on machines with a real FORGEJO_TOKEN already
        # in the environment (e.g. from other forge sync work in the same
        # shell) — a clean CI container has none, so execute_sync returned
        # a "No Forgejo token found" error before ever reaching the mocked
        # ForgejoClient.list_issues call, and this test failed there first.
        with patch("autonomous_forge.sync.ForgejoClient.list_issues", return_value=[]), \
             patch("autonomous_forge.sync._load_token", return_value="fake-token"):
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
