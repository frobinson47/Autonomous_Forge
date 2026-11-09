"""Tests for the two backlink guards from AUTO-075's Risks (duplicate and dropped backlinks)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from autonomous_forge.drift import collect_drift_signals
from autonomous_forge.sync import SyncResult, execute_sync

PLAN = """\
## Roadmap v1

### AUTO-001 — Build the widget
Priority: P1
Status: DONE

Goal: Build a widget.

### AUTO-002 — Test the widget
Priority: P2
Status: TODO

Goal: Write tests for the widget.
"""

LINKED = PLAN.replace(
    "Goal: Write tests for the widget.\n",
    "Goal: Write tests for the widget.\nNotes: Imported from Forgejo issue #42.\n",
)


def _plan_with_notes(note_a: str, note_b: str) -> str:
    return (
        "### AUTO-001 — First\nPriority: P1\nStatus: DONE\n"
        f"Notes: {note_a}\n\n"
        "### AUTO-002 — Second\nPriority: P2\nStatus: DONE\n"
        f"Notes: {note_b}\n"
    )


class TestDuplicateBacklinks:
    def test_signal_when_two_tasks_backlink_the_same_issue(self):
        plan = _plan_with_notes("Forgejo issue #80.", "see Forgejo issue #80 too")
        dup = [s for s in collect_drift_signals(plan) if s.category == "duplicate-backlink"]
        assert len(dup) == 1
        assert "#80" in dup[0].message
        assert "AUTO-001" in dup[0].message
        assert "AUTO-002" in dup[0].message

    def test_no_signal_for_distinct_issues(self):
        plan = _plan_with_notes("Forgejo issue #80.", "Forgejo issue #81.")
        signals = collect_drift_signals(plan)
        assert [s for s in signals if s.category == "duplicate-backlink"] == []

    def test_no_signal_without_backlinks(self):
        plan = _plan_with_notes("nothing", "nothing")
        signals = collect_drift_signals(plan)
        assert [s for s in signals if s.category == "duplicate-backlink"] == []


def _git(root: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603, S607 — test helper, fixed argv
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _repo(tmp_path: Path, committed: str, working: str) -> None:
    (tmp_path / ".ai").mkdir()
    plan = tmp_path / ".ai" / "AUTONOMOUS_PLAN.md"
    plan.write_text(committed, encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "plan")
    plan.write_text(working, encoding="utf-8")


def _dry_run(tmp_path: Path, issues: list[dict]) -> SyncResult:
    with patch("autonomous_forge.sync.ForgejoClient.list_issues", return_value=issues):
        return execute_sync(
            root=tmp_path,
            dry_run=True,
            repo_override="frank/Test",
            token_override="fake-token",
        )


class TestDroppedBacklinkGuard:
    """A Notes edit that drops ``Forgejo issue #N`` would make sync plan a duplicate."""

    def test_uncommitted_backlink_removal_blocks_duplicate(self, tmp_path: Path):
        _repo(tmp_path, committed=LINKED, working=PLAN)
        # Issue #42 exists with an unrelated title, so only the backlink linked it.
        result = _dry_run(tmp_path, [{"title": "Widget tests", "number": 42}])
        action = next(a for a in result.actions if a.task_id == "AUTO-002")
        assert action.action == "error"
        assert "#42" in action.detail
        assert any("AUTO-002" in e and "#42" in e for e in result.errors)

    def test_committed_backlink_removal_is_deliberate(self, tmp_path: Path):
        _repo(tmp_path, committed=PLAN, working=PLAN)
        result = _dry_run(tmp_path, [{"title": "Widget tests", "number": 42}])
        action = next(a for a in result.actions if a.task_id == "AUTO-002")
        assert action.action == "would-create"
        assert not result.errors

    def test_intact_backlink_is_unaffected(self, tmp_path: Path):
        _repo(tmp_path, committed=LINKED, working=LINKED)
        result = _dry_run(tmp_path, [{"title": "Widget tests", "number": 42}])
        action = next(a for a in result.actions if a.task_id == "AUTO-002")
        assert action.action == "would-sync"
        assert not result.errors

    def test_no_git_history_means_no_guard(self, tmp_path: Path):
        (tmp_path / ".ai").mkdir()
        (tmp_path / ".ai" / "AUTONOMOUS_PLAN.md").write_text(PLAN, encoding="utf-8")
        result = _dry_run(tmp_path, [])
        assert all(a.action == "would-create" for a in result.actions)
        assert not result.errors
