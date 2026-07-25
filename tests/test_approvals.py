"""Tests for recording and checking human approvals."""

from __future__ import annotations

from pathlib import Path

from autonomous_forge.approvals import (
    format_approval_confirmation,
    has_approval,
    parse_approvals,
    record_approval,
)


class TestParseApprovals:
    def test_parses_records(self):
        text = """# Human Approvals

## AUTO-001 — Adding network access.
Approved: 2026-07-25T12:00:00+00:00
Note: Reviewed diff, only calls the Forgejo API.

## AUTO-002 — Adding telemetry.
Approved: 2026-07-25T13:00:00+00:00
"""
        records = parse_approvals(text)
        assert len(records) == 2
        assert records[0].task_id == "AUTO-001"
        assert records[0].category == "Adding network access."
        assert records[0].note == "Reviewed diff, only calls the Forgejo API."
        assert records[1].task_id == "AUTO-002"
        assert records[1].note == ""

    def test_empty_text_returns_no_records(self):
        assert parse_approvals("") == []


class TestHasApproval:
    def test_missing_file_returns_false(self, tmp_path: Path):
        assert not has_approval("AUTO-001", root=tmp_path)

    def test_no_matching_record_returns_false(self, tmp_path: Path):
        (tmp_path / ".forge").mkdir()
        (tmp_path / ".forge/approvals.md").write_text(
            "# Human Approvals\n\n## AUTO-002 — Something else.\nApproved: 2026-07-25T00:00:00+00:00\n",
            encoding="utf-8",
        )
        assert not has_approval("AUTO-001", root=tmp_path)

    def test_matching_record_returns_true(self, tmp_path: Path):
        (tmp_path / ".forge").mkdir()
        (tmp_path / ".forge/approvals.md").write_text(
            "# Human Approvals\n\n## AUTO-001 — Adding network access.\nApproved: 2026-07-25T00:00:00+00:00\n",
            encoding="utf-8",
        )
        assert has_approval("AUTO-001", root=tmp_path)


class TestRecordApproval:
    def test_creates_file_with_header(self, tmp_path: Path):
        path = record_approval(
            "AUTO-001", "Adding network access.",
            root=tmp_path, timestamp="2026-07-25T00:00:00+00:00",
        )
        text = path.read_text(encoding="utf-8")
        assert text.startswith("# Human Approvals")
        assert "## AUTO-001 — Adding network access." in text
        assert "Approved: 2026-07-25T00:00:00+00:00" in text

    def test_includes_note_when_given(self, tmp_path: Path):
        path = record_approval(
            "AUTO-001", "Adding network access.",
            root=tmp_path, note="Reviewed and approved.",
            timestamp="2026-07-25T00:00:00+00:00",
        )
        assert "Note: Reviewed and approved." in path.read_text(encoding="utf-8")

    def test_appends_to_existing_file(self, tmp_path: Path):
        record_approval(
            "AUTO-001", "Adding network access.",
            root=tmp_path, timestamp="2026-07-25T00:00:00+00:00",
        )
        record_approval(
            "AUTO-002", "Adding telemetry.",
            root=tmp_path, timestamp="2026-07-25T01:00:00+00:00",
        )
        records = parse_approvals(
            (tmp_path / ".forge/approvals.md").read_text(encoding="utf-8")
        )
        assert [r.task_id for r in records] == ["AUTO-001", "AUTO-002"]

    def test_round_trips_through_has_approval(self, tmp_path: Path):
        record_approval("AUTO-005", "Adding network access.", root=tmp_path)
        assert has_approval("AUTO-005", root=tmp_path)


class TestFormatApprovalConfirmation:
    def test_includes_task_and_path(self, tmp_path: Path):
        path = tmp_path / ".forge/approvals.md"
        text = format_approval_confirmation("AUTO-001", "Adding network access.", path)
        assert "AUTO-001" in text
        assert "Adding network access." in text
        assert str(path) in text
