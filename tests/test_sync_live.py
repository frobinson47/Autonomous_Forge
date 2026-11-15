"""Tests for the live (non-dry-run) write path of ``execute_sync`` (AUTO-077).

A mocked ``ForgejoClient`` records every call, so each test asserts exactly
what a live run would write to Forgejo.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from autonomous_forge.sync import SyncResult, execute_sync

LABELS = [
    {"name": "status:todo", "id": 1},
    {"name": "status:done", "id": 2},
    {"name": "status:blocked", "id": 3},
    {"name": "status:skipped", "id": 4},
    {"name": "priority:critical", "id": 5},
    {"name": "priority:high", "id": 6},
    {"name": "priority:medium", "id": 7},
    {"name": "priority:low", "id": 8},
    {"name": "forge-sync", "id": 9},
]

# Label ids a task gets: status label, priority label, forge-sync.
TODO_P2_LABELS = [1, 7, 9]
DONE_P1_LABELS = [2, 6, 9]


def _plan(*tasks: tuple[str, str, str], heading: str = "## Roadmap v1") -> str:
    parts = [heading, ""]
    for task_id, priority, status in tasks:
        parts += [
            f"### {task_id} — Title of {task_id}",
            f"Priority: {priority}",
            f"Status: {status}",
            "",
            f"Goal: Goal of {task_id}.",
            "",
        ]
    return "\n".join(parts)


def _client(issues: list[dict] | None = None, milestones: list[dict] | None = None) -> MagicMock:
    client = MagicMock()
    client.list_labels.return_value = [dict(lab) for lab in LABELS]
    client.list_issues.return_value = issues or []
    client.list_milestones.return_value = milestones if milestones is not None else []
    client.create_milestone.return_value = {"id": 50}
    client.create_issue.return_value = {"number": 101}
    return client


def _run(tmp_path: Path, plan_text: str, client: MagicMock) -> SyncResult:
    ai_dir = tmp_path / ".ai"
    ai_dir.mkdir()
    (ai_dir / "AUTONOMOUS_PLAN.md").write_text(plan_text, encoding="utf-8")
    with patch("autonomous_forge.sync.ForgejoClient", return_value=client):
        return execute_sync(
            root=tmp_path,
            repo_override="frank/Test",
            token_override="fake-token",
        )


def _issue(number: int, task_id: str, state: str, label_ids: list[int], milestone_id: int | None):
    return {
        "number": number,
        "title": f"[{task_id}] Title of {task_id}",
        "state": state,
        "labels": [{"id": i} for i in label_ids],
        "milestone": {"id": milestone_id} if milestone_id is not None else None,
    }


class TestLiveCreate:
    def test_new_todo_task_creates_open_issue_with_labels_and_milestone(self, tmp_path):
        client = _client()
        result = _run(tmp_path, _plan(("AUTO-001", "P2", "TODO")), client)

        client.create_issue.assert_called_once()
        kwargs = client.create_issue.call_args.kwargs
        assert kwargs["title"] == "[AUTO-001] Title of AUTO-001"
        assert kwargs["labels"] == TODO_P2_LABELS
        assert kwargs["milestone"] == 50
        assert "**Task ID:** AUTO-001" in kwargs["body"]
        client.update_issue.assert_not_called()
        client.add_comment.assert_not_called()
        assert [(a.action, a.issue_number) for a in result.actions] == [("created", 101)]
        assert not result.errors

    def test_new_done_task_is_created_then_closed_with_comment(self, tmp_path):
        client = _client()
        result = _run(tmp_path, _plan(("AUTO-001", "P1", "DONE")), client)

        assert client.create_issue.call_args.kwargs["labels"] == DONE_P1_LABELS
        client.update_issue.assert_called_once_with(101, state="closed")
        client.add_comment.assert_called_once()
        assert client.add_comment.call_args.args[0] == 101
        assert "DONE" in client.add_comment.call_args.args[1]
        assert result.actions[0].action == "created"

    def test_missing_labels_are_created_first(self, tmp_path):
        client = _client()
        client.list_labels.return_value = []
        client.create_label.side_effect = lambda name, color: {"id": 100 + len(name)}
        _run(tmp_path, _plan(("AUTO-001", "P2", "TODO")), client)

        created = {c.args[0] for c in client.create_label.call_args_list}
        assert created == {lab["name"] for lab in LABELS}

    def test_existing_milestone_is_reused_not_recreated(self, tmp_path):
        client = _client(milestones=[{"title": "Roadmap v1", "id": 7}])
        _run(tmp_path, _plan(("AUTO-001", "P2", "TODO")), client)

        client.create_milestone.assert_not_called()
        assert client.create_issue.call_args.kwargs["milestone"] == 7

    def test_milestone_created_once_for_several_tasks_in_one_roadmap(self, tmp_path):
        client = _client()
        client.create_issue.side_effect = [{"number": 101}, {"number": 102}]
        _run(tmp_path, _plan(("AUTO-001", "P2", "TODO"), ("AUTO-002", "P2", "TODO")), client)

        client.create_milestone.assert_called_once_with("Roadmap v1")
        assert client.create_issue.call_count == 2

    def test_task_outside_a_roadmap_section_gets_no_milestone(self, tmp_path):
        client = _client()
        _run(tmp_path, _plan(("AUTO-001", "P2", "TODO"), heading="## Backlog"), client)

        assert "milestone" not in client.create_issue.call_args.kwargs
        client.create_milestone.assert_not_called()


class TestLiveUpdate:
    def test_open_issue_for_done_task_is_closed_with_comment(self, tmp_path):
        issue = _issue(9, "AUTO-001", "open", DONE_P1_LABELS, 50)
        client = _client(issues=[issue], milestones=[{"title": "Roadmap v1", "id": 50}])
        result = _run(tmp_path, _plan(("AUTO-001", "P1", "DONE")), client)

        client.create_issue.assert_not_called()
        client.update_issue.assert_called_once_with(9, state="closed")
        assert client.add_comment.call_args.args[0] == 9
        assert "DONE" in client.add_comment.call_args.args[1]
        client.replace_labels.assert_not_called()
        assert (result.actions[0].action, result.actions[0].issue_number) == ("closed", 9)

    def test_closed_issue_for_todo_task_is_reopened_with_comment(self, tmp_path):
        issue = _issue(9, "AUTO-001", "closed", TODO_P2_LABELS, 50)
        client = _client(issues=[issue], milestones=[{"title": "Roadmap v1", "id": 50}])
        result = _run(tmp_path, _plan(("AUTO-001", "P2", "TODO")), client)

        client.update_issue.assert_called_once_with(9, state="open")
        assert "TODO" in client.add_comment.call_args.args[1]
        assert result.actions[0].action == "reopened"

    def test_labels_replaced_only_when_they_differ(self, tmp_path):
        issue = _issue(9, "AUTO-001", "open", [1, 8], 50)  # wrong priority, no forge-sync
        client = _client(issues=[issue], milestones=[{"title": "Roadmap v1", "id": 50}])
        result = _run(tmp_path, _plan(("AUTO-001", "P2", "TODO")), client)

        client.replace_labels.assert_called_once_with(9, TODO_P2_LABELS)
        client.update_issue.assert_not_called()
        assert result.actions[0].action == "labels updated"

    def test_label_order_does_not_trigger_a_replace(self, tmp_path):
        issue = _issue(9, "AUTO-001", "open", [9, 7, 1], 50)  # same set, different order
        client = _client(issues=[issue], milestones=[{"title": "Roadmap v1", "id": 50}])
        result = _run(tmp_path, _plan(("AUTO-001", "P2", "TODO")), client)

        client.replace_labels.assert_not_called()
        assert result.actions[0].action == "up-to-date"

    def test_wrong_or_missing_milestone_is_updated(self, tmp_path):
        issue = _issue(9, "AUTO-001", "open", TODO_P2_LABELS, None)
        client = _client(issues=[issue], milestones=[{"title": "Roadmap v1", "id": 50}])
        result = _run(tmp_path, _plan(("AUTO-001", "P2", "TODO")), client)

        client.update_issue.assert_called_once_with(9, milestone=50)
        assert result.actions[0].action == "milestone updated"

    def test_several_changes_are_reported_together(self, tmp_path):
        issue = _issue(9, "AUTO-001", "open", [1], None)
        client = _client(issues=[issue], milestones=[{"title": "Roadmap v1", "id": 50}])
        result = _run(tmp_path, _plan(("AUTO-001", "P1", "DONE")), client)

        assert result.actions[0].action == "closed, labels updated, milestone updated"

    def test_up_to_date_task_makes_no_write_calls(self, tmp_path):
        issue = _issue(9, "AUTO-001", "closed", DONE_P1_LABELS, 50)
        client = _client(issues=[issue], milestones=[{"title": "Roadmap v1", "id": 50}])
        result = _run(tmp_path, _plan(("AUTO-001", "P1", "DONE")), client)

        client.create_issue.assert_not_called()
        client.update_issue.assert_not_called()
        client.add_comment.assert_not_called()
        client.replace_labels.assert_not_called()
        assert result.actions[0].action == "up-to-date"

    def test_blocked_task_never_closes_or_reopens(self, tmp_path):
        issue = _issue(9, "AUTO-001", "open", [3, 6, 9], 50)
        client = _client(issues=[issue], milestones=[{"title": "Roadmap v1", "id": 50}])
        result = _run(tmp_path, _plan(("AUTO-001", "P1", "BLOCKED")), client)

        client.update_issue.assert_not_called()
        assert result.actions[0].action == "up-to-date"


class TestLiveFailures:
    def test_error_on_one_task_does_not_stop_the_rest(self, tmp_path):
        client = _client()
        client.create_issue.side_effect = [RuntimeError("boom"), {"number": 102}]
        result = _run(
            tmp_path, _plan(("AUTO-001", "P2", "TODO"), ("AUTO-002", "P2", "TODO")), client
        )

        assert [a.action for a in result.actions] == ["error", "created"]
        assert result.actions[1].issue_number == 102
        assert result.errors == ("AUTO-001: boom",)

    def test_label_setup_failure_aborts_before_any_issue_is_written(self, tmp_path):
        client = _client()
        client.list_labels.side_effect = RuntimeError("labels down")
        result = _run(tmp_path, _plan(("AUTO-001", "P2", "TODO")), client)

        assert result.actions == ()
        assert result.errors == ("labels down",)
        client.create_issue.assert_not_called()

    def test_issue_listing_failure_aborts_before_any_issue_is_written(self, tmp_path):
        client = _client()
        client.list_issues.side_effect = RuntimeError("issues down")
        result = _run(tmp_path, _plan(("AUTO-001", "P2", "TODO")), client)

        assert result.actions == ()
        assert result.errors == ("issues down",)
        client.create_issue.assert_not_called()

    def test_failure_closing_a_new_done_issue_is_an_error_not_a_crash(self, tmp_path):
        client = _client()
        client.update_issue.side_effect = RuntimeError("close failed")
        result = _run(tmp_path, _plan(("AUTO-001", "P1", "DONE")), client)

        assert result.actions[0].action == "error"
        assert result.errors == ("AUTO-001: close failed",)
