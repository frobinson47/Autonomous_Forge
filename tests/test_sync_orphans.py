"""Tests for read-only orphan-issue reporting and explicit orphan import."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from autonomous_forge.plan import PlanTask
from autonomous_forge.sync_orphans import (
    ImportedTask,
    ImportResult,
    OrphanIssue,
    OrphanReport,
    execute_import_orphans,
    execute_orphan_report,
    find_orphan_issues,
    format_import_result,
    format_orphan_report,
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
        with patch("autonomous_forge.sync_orphans._detect_forgejo_repo", return_value=None):
            report = execute_orphan_report(root=tmp_path)
        assert report.errors
        assert "Could not detect" in report.errors[0]

    def test_no_token(self, tmp_path: Path):
        self._setup_plan(tmp_path)
        with patch("autonomous_forge.sync_orphans._load_token", return_value=None):
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
        with patch("autonomous_forge.sync_orphans.ForgejoClient", return_value=mock_client):
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
        with patch("autonomous_forge.sync_orphans.ForgejoClient", return_value=mock_client):
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


class TestExecuteImportOrphans:
    def _setup_plan(self, tmp_path: Path, plan_text: str = SYNC_PLAN):
        ai_dir = tmp_path / ".ai"
        ai_dir.mkdir()
        (ai_dir / "AUTONOMOUS_PLAN.md").write_text(plan_text, encoding="utf-8")

    def test_no_repo_detected(self, tmp_path: Path):
        self._setup_plan(tmp_path)
        with patch("autonomous_forge.sync_orphans._detect_forgejo_repo", return_value=None):
            result = execute_import_orphans(root=tmp_path)
        assert result.errors
        assert result.imported == ()

    def test_no_token(self, tmp_path: Path):
        self._setup_plan(tmp_path)
        with patch("autonomous_forge.sync_orphans._load_token", return_value=None):
            result = execute_import_orphans(root=tmp_path, repo_override="frank/Test")
        assert result.errors

    def test_imports_orphan_as_new_task_stub(self, tmp_path: Path):
        self._setup_plan(tmp_path)
        mock_client = MagicMock()
        mock_client.list_issues.return_value = [
            {"number": 5, "state": "open", "title": "Manually filed bug",
             "html_url": "https://forgejo.example/frank/Test/issues/5"},
            {"number": 1, "state": "open", "title": "[AUTO-001] Build the widget"},
        ]
        with patch("autonomous_forge.sync_orphans.ForgejoClient", return_value=mock_client):
            result = execute_import_orphans(
                root=tmp_path, repo_override="frank/Test", token_override="fake-token",
            )

        assert len(result.imported) == 1
        imported = result.imported[0]
        assert imported.title == "Manually filed bug"
        assert imported.source_issue_number == 5
        assert imported.task_id.startswith("AUTO-")

        plan_text = (tmp_path / ".ai/AUTONOMOUS_PLAN.md").read_text(encoding="utf-8")
        assert f"### {imported.task_id} — Manually filed bug" in plan_text
        assert "Forgejo issue #5" in plan_text
        assert "https://forgejo.example/frank/Test/issues/5" in plan_text
        assert "Status: TODO" in plan_text

        # write only — no Forgejo mutation calls of any kind.
        mock_client.create_issue.assert_not_called()
        mock_client.update_issue.assert_not_called()
        mock_client.add_comment.assert_not_called()

    def test_no_orphans_imports_nothing(self, tmp_path: Path):
        self._setup_plan(tmp_path)
        mock_client = MagicMock()
        mock_client.list_issues.return_value = [
            {"number": 1, "state": "open", "title": "[AUTO-001] Build the widget"},
        ]
        with patch("autonomous_forge.sync_orphans.ForgejoClient", return_value=mock_client):
            result = execute_import_orphans(
                root=tmp_path, repo_override="frank/Test", token_override="fake-token",
            )
        assert result.imported == ()
        assert result.already_imported == ()

    def test_rerun_is_idempotent(self, tmp_path: Path):
        self._setup_plan(tmp_path)
        mock_client = MagicMock()
        mock_client.list_issues.return_value = [
            {"number": 5, "state": "open", "title": "Manually filed bug",
             "html_url": "https://forgejo.example/frank/Test/issues/5"},
            {"number": 1, "state": "open", "title": "[AUTO-001] Build the widget"},
        ]
        with patch("autonomous_forge.sync_orphans.ForgejoClient", return_value=mock_client):
            first = execute_import_orphans(
                root=tmp_path, repo_override="frank/Test", token_override="fake-token",
            )
            second = execute_import_orphans(
                root=tmp_path, repo_override="frank/Test", token_override="fake-token",
            )

        assert len(first.imported) == 1
        assert second.imported == ()
        assert second.already_imported == (5,)

        plan_text = (tmp_path / ".ai/AUTONOMOUS_PLAN.md").read_text(encoding="utf-8")
        assert plan_text.count("Manually filed bug") == 2  # heading + Goal line, not duplicated

    def test_multiple_orphans_get_distinct_incrementing_ids(self, tmp_path: Path):
        self._setup_plan(tmp_path)
        mock_client = MagicMock()
        mock_client.list_issues.return_value = [
            {"number": 5, "state": "open", "title": "First orphan",
             "html_url": "https://forgejo.example/frank/Test/issues/5"},
            {"number": 9, "state": "open", "title": "Second orphan",
             "html_url": "https://forgejo.example/frank/Test/issues/9"},
        ]
        with patch("autonomous_forge.sync_orphans.ForgejoClient", return_value=mock_client):
            result = execute_import_orphans(
                root=tmp_path, repo_override="frank/Test", token_override="fake-token",
            )

        assert len(result.imported) == 2
        ids = {t.task_id for t in result.imported}
        assert len(ids) == 2  # distinct IDs, no collision


class TestFormatImportResult:
    def test_no_orphans(self):
        result = ImportResult(imported=(), already_imported=(), repo="frank/Test")
        text = format_import_result(result)
        assert "No orphan issues to import" in text

    def test_with_imported(self):
        result = ImportResult(
            imported=(ImportedTask(task_id="AUTO-043", title="Manually filed bug", source_issue_number=5),),
            already_imported=(),
            repo="frank/Test",
        )
        text = format_import_result(result)
        assert "Imported: 1" in text
        assert "AUTO-043" in text
        assert "#5" in text

    def test_with_already_imported(self):
        result = ImportResult(imported=(), already_imported=(5, 9), repo="frank/Test")
        text = format_import_result(result)
        assert "Already imported (skipped): 2" in text
        assert "#5" in text
        assert "#9" in text

    def test_with_errors(self):
        result = ImportResult(imported=(), already_imported=(), repo="frank/Test", errors=("No token found.",))
        text = format_import_result(result)
        assert "ERROR" in text


class TestSyncOrphansCLI:
    def test_report_orphans_cli(self, tmp_path: Path, capsys):
        ai_dir = tmp_path / ".ai"
        ai_dir.mkdir()
        (ai_dir / "AUTONOMOUS_PLAN.md").write_text(SYNC_PLAN, encoding="utf-8")

        from autonomous_forge.cli import main

        mock_client = MagicMock()
        mock_client.list_issues.return_value = [
            {"number": 5, "state": "open", "title": "Manually filed bug"},
        ]
        with patch("autonomous_forge.sync_orphans.ForgejoClient", return_value=mock_client), \
             patch("autonomous_forge.sync_orphans._load_token", return_value="fake-token"):
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

    def test_import_orphans_cli(self, tmp_path: Path, capsys):
        ai_dir = tmp_path / ".ai"
        ai_dir.mkdir()
        (ai_dir / "AUTONOMOUS_PLAN.md").write_text(SYNC_PLAN, encoding="utf-8")

        from autonomous_forge.cli import main

        mock_client = MagicMock()
        mock_client.list_issues.return_value = [
            {"number": 5, "state": "open", "title": "Manually filed bug",
             "html_url": "https://forgejo.example/frank/Test/issues/5"},
        ]
        with patch("autonomous_forge.sync_orphans.ForgejoClient", return_value=mock_client), \
             patch("autonomous_forge.sync_orphans._load_token", return_value="fake-token"):
            code = main([
                "sync",
                "--root", str(tmp_path),
                "--plan", str(ai_dir / "AUTONOMOUS_PLAN.md"),
                "--repo", "frank/Test",
                "--import-orphans",
            ])
        captured = capsys.readouterr()
        assert code == 0
        assert "Imported: 1" in captured.out
        assert "Manually filed bug" in captured.out
        mock_client.create_issue.assert_not_called()

        plan_text = (ai_dir / "AUTONOMOUS_PLAN.md").read_text(encoding="utf-8")
        assert "Manually filed bug" in plan_text
        assert "Forgejo issue #5" in plan_text
