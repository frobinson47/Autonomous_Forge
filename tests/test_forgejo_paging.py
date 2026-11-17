"""Tests that every Forgejo list call pages through all results (AUTO-079).

Forgejo caps a page at 50 items, so a call that asks once silently drops
everything past the first 50.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from autonomous_forge.forgejo_client import ForgejoClient


def _client() -> ForgejoClient:
    return ForgejoClient("o/r", "tok", base_url="https://x")


def _labels(start: int, count: int) -> list[dict]:
    return [{"id": i, "name": f"label-{i}"} for i in range(start, start + count)]


def _milestones(start: int, count: int) -> list[dict]:
    return [{"id": i, "title": f"m-{i}"} for i in range(start, start + count)]


class TestListLabelsPaging:
    def test_fetches_every_page(self):
        pages = [_labels(0, 50), _labels(50, 7)]
        with patch.object(ForgejoClient, "_request", side_effect=pages) as req:
            result = _client().list_labels()
        assert len(result) == 57
        assert result[-1]["name"] == "label-56"
        assert [c.args[1] for c in req.call_args_list] == [
            "/labels?limit=50&page=1",
            "/labels?limit=50&page=2",
        ]

    def test_a_full_last_page_is_followed_by_one_empty_page(self):
        with patch.object(ForgejoClient, "_request", side_effect=[_labels(0, 50), []]) as req:
            result = _client().list_labels()
        assert len(result) == 50
        assert req.call_count == 2

    def test_a_single_short_page_makes_one_request(self):
        with patch.object(ForgejoClient, "_request", return_value=_labels(0, 3)) as req:
            assert len(_client().list_labels()) == 3
        assert req.call_count == 1

    def test_empty_reply_is_an_empty_list(self):
        with patch.object(ForgejoClient, "_request", return_value=None):
            assert _client().list_labels() == []

    def test_a_malformed_later_page_still_raises_cleanly(self):
        bad = [{"id": 1}]  # missing "name"
        with patch.object(ForgejoClient, "_request", side_effect=[_labels(0, 50), bad]):
            with pytest.raises(RuntimeError, match="name"):
                _client().list_labels()


class TestListMilestonesPaging:
    def test_fetches_every_page_and_keeps_the_state_filter(self):
        pages = [_milestones(0, 50), _milestones(50, 2)]
        with patch.object(ForgejoClient, "_request", side_effect=pages) as req:
            result = _client().list_milestones(state="open")
        assert len(result) == 52
        assert [c.args[1] for c in req.call_args_list] == [
            "/milestones?state=open&limit=50&page=1",
            "/milestones?state=open&limit=50&page=2",
        ]

    def test_empty_reply_is_an_empty_list(self):
        with patch.object(ForgejoClient, "_request", return_value=[]):
            assert _client().list_milestones() == []


class TestListIssuesStillPages:
    def test_keeps_its_query_string_and_pages(self):
        pages = [[{"number": 1}, {"number": 2}], [{"number": 3}]]
        with patch.object(ForgejoClient, "_request", side_effect=pages) as req:
            result = _client().list_issues(state="open", limit=2)
        assert [i["number"] for i in result] == [1, 2, 3]
        assert [c.args[1] for c in req.call_args_list] == [
            "/issues?state=open&type=issues&limit=2&page=1",
            "/issues?state=open&type=issues&limit=2&page=2",
        ]


class TestRunawayPagingGuard:
    def test_server_that_ignores_the_page_parameter_cannot_loop_forever(self):
        full_page = _labels(0, 50)
        with patch.object(ForgejoClient, "_request", return_value=full_page) as req:
            with pytest.raises(RuntimeError, match="pages"):
                _client().list_labels()
        assert req.call_count < 1000
