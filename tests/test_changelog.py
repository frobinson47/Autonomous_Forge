"""Tests for auto-appending completed tasks to the changelog."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from autonomous_forge.changelog import append_changelog_entries, find_newly_done_tasks
from autonomous_forge.plan import PlanTask

PLAN_ONE_DONE = """\
# Roadmap

### AUTO-001 — Build widget
Priority: P1
Status: DONE

Goal: Build a widget.

### AUTO-002 — Polish widget
Priority: P2
Status: TODO

Goal: Polish it.
"""

PLAN_BOTH_TODO = """\
# Roadmap

### AUTO-001 — Build widget
Priority: P1
Status: TODO

Goal: Build a widget.

### AUTO-002 — Polish widget
Priority: P2
Status: TODO

Goal: Polish it.
"""

PLAN_BOTH_DONE = """\
# Roadmap

### AUTO-001 — Build widget
Priority: P1
Status: DONE

Goal: Build a widget.

### AUTO-002 — Polish widget
Priority: P2
Status: DONE

Goal: Polish it.
"""


def _setup(tmp_path: Path, plan_text: str) -> Path:
    (tmp_path / ".ai").mkdir()
    plan_path = tmp_path / ".ai" / "AUTONOMOUS_PLAN.md"
    plan_path.write_text(plan_text, encoding="utf-8")
    return plan_path


class TestFindNewlyDoneTasks:
    def test_detects_task_newly_done_since_head(self, tmp_path: Path):
        _setup(tmp_path, PLAN_ONE_DONE)
        with patch("autonomous_forge.changelog.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=PLAN_BOTH_TODO.encode("utf-8"))
            newly_done = find_newly_done_tasks(tmp_path)

        assert [t.task_id for t in newly_done] == ["AUTO-001"]

    def test_no_change_returns_empty(self, tmp_path: Path):
        _setup(tmp_path, PLAN_ONE_DONE)
        with patch("autonomous_forge.changelog.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=PLAN_ONE_DONE.encode("utf-8"))
            newly_done = find_newly_done_tasks(tmp_path)

        assert newly_done == ()

    def test_multiple_newly_done_tasks(self, tmp_path: Path):
        _setup(tmp_path, PLAN_BOTH_DONE)
        with patch("autonomous_forge.changelog.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=PLAN_BOTH_TODO.encode("utf-8"))
            newly_done = find_newly_done_tasks(tmp_path)

        assert {t.task_id for t in newly_done} == {"AUTO-001", "AUTO-002"}

    def test_no_head_version_treats_all_done_as_new(self, tmp_path: Path):
        # No prior commit (e.g. first commit ever) — git show fails.
        _setup(tmp_path, PLAN_ONE_DONE)
        with patch("autonomous_forge.changelog.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=128, stdout="")
            newly_done = find_newly_done_tasks(tmp_path)

        assert [t.task_id for t in newly_done] == ["AUTO-001"]

    def test_missing_plan_returns_empty(self, tmp_path: Path):
        newly_done = find_newly_done_tasks(tmp_path)
        assert newly_done == ()

    def test_already_done_at_head_is_not_newly_done(self, tmp_path: Path):
        _setup(tmp_path, PLAN_ONE_DONE)
        with patch("autonomous_forge.changelog.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=PLAN_ONE_DONE.encode("utf-8"))
            newly_done = find_newly_done_tasks(tmp_path)

        assert newly_done == ()


class TestAppendChangelogEntries:
    def _task(self, task_id="AUTO-001", title="Build widget"):
        return PlanTask(task_id=task_id, title=title, priority="P1", status="DONE", line_number=1)

    def test_appends_one_line_per_task(self, tmp_path: Path):
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n\n## Existing entry\n\n- old content\n", encoding="utf-8")

        result_path = append_changelog_entries(
            (self._task("AUTO-001", "Build widget"), self._task("AUTO-002", "Polish widget")),
            changelog_path=changelog,
            timestamp="2026-07-24T00:00:00+00:00",
        )

        assert result_path == changelog
        text = changelog.read_text(encoding="utf-8")
        assert "- old content" in text
        assert "- 2026-07-24: AUTO-001 — Build widget (DONE)" in text
        assert "- 2026-07-24: AUTO-002 — Polish widget (DONE)" in text

    def test_preserves_existing_content_verbatim(self, tmp_path: Path):
        changelog = tmp_path / "CHANGELOG.md"
        original = "# Changelog\n\n## 2026-01-01 — AUTO-000\n\n- Task ID: AUTO-000\n- Summary: bootstrap\n"
        changelog.write_text(original, encoding="utf-8")

        append_changelog_entries(
            (self._task(),), changelog_path=changelog, timestamp="2026-07-24T00:00:00+00:00",
        )

        text = changelog.read_text(encoding="utf-8")
        assert text.startswith(original.rstrip("\n"))

    def test_no_tasks_returns_none_and_does_not_touch_file(self, tmp_path: Path):
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n", encoding="utf-8")

        result = append_changelog_entries((), changelog_path=changelog)

        assert result is None
        assert changelog.read_text(encoding="utf-8") == "# Changelog\n"

    def test_missing_changelog_file_returns_none(self, tmp_path: Path):
        changelog = tmp_path / "does_not_exist.md"
        result = append_changelog_entries((self._task(),), changelog_path=changelog)
        assert result is None
        assert not changelog.exists()
