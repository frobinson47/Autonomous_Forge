"""Tests for the forge doctor diagnostic command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from autonomous_forge.doctor import (
    DoctorCheck,
    DoctorReport,
    format_doctor_report,
    run_doctor,
)


def _make_repo(tmp_path: Path, with_policy: bool = True) -> Path:
    (tmp_path / ".ai").mkdir()
    (tmp_path / ".ai" / "AUTONOMOUS_PLAN.md").write_text("# Roadmap\n", encoding="utf-8")
    if with_policy:
        (tmp_path / ".forge").mkdir()
        (tmp_path / ".forge" / "policy.md").write_text("# Policy\n", encoding="utf-8")
    return tmp_path


class TestDoctorReport:
    def test_all_passed_true_when_all_pass(self):
        report = DoctorReport(checks=(
            DoctorCheck("a", True, "ok"),
            DoctorCheck("b", True, "ok"),
        ))
        assert report.all_passed is True

    def test_all_passed_false_when_any_fails(self):
        report = DoctorReport(checks=(
            DoctorCheck("a", True, "ok"),
            DoctorCheck("b", False, "bad"),
        ))
        assert report.all_passed is False

    def test_all_passed_true_when_only_skipped(self):
        report = DoctorReport(checks=(
            DoctorCheck("a", True, "ok"),
            DoctorCheck("b", None, "skipped"),
        ))
        assert report.all_passed is True


class TestFormatDoctorReport:
    def test_shows_pass_fail_skip(self):
        report = DoctorReport(checks=(
            DoctorCheck("git available", True, "git version 2.40"),
            DoctorCheck("policy file present", False, "not found", hint="run forge init"),
            DoctorCheck("Forgejo repo reachable", None, "skipped"),
        ))
        text = format_doctor_report(report)
        assert "git available: PASS" in text
        assert "policy file present: FAIL" in text
        assert "hint: run forge init" in text
        assert "Forgejo repo reachable: SKIP" in text
        assert "Result: ISSUES FOUND" in text

    def test_all_passed_result_line(self):
        report = DoctorReport(checks=(DoctorCheck("git available", True, "ok"),))
        assert "Result: ALL PASSED" in format_doctor_report(report)


class TestRunDoctor:
    def test_reports_missing_plan_and_policy(self, tmp_path: Path):
        with patch("autonomous_forge.doctor.subprocess.run") as mock_git, \
             patch("autonomous_forge.doctor._load_token", return_value=None), \
             patch("autonomous_forge.doctor._detect_forgejo_repo", return_value=None):
            mock_git.return_value = MagicMock(returncode=0, stdout="git version 2.40.0")
            report = run_doctor(tmp_path)

        by_name = {c.name: c for c in report.checks}
        assert by_name["plan file present"].passed is False
        assert by_name["policy file present"].passed is False
        assert by_name["Forgejo token present"].passed is False
        assert by_name["Forgejo remote detected"].passed is False
        assert by_name["Forgejo repo reachable"].passed is None
        assert report.all_passed is False

    def test_reports_healthy_repo_without_network(self, tmp_path: Path):
        _make_repo(tmp_path)
        with patch("autonomous_forge.doctor.subprocess.run") as mock_git, \
             patch("autonomous_forge.doctor._load_token", return_value="tok"), \
             patch("autonomous_forge.doctor._detect_forgejo_repo", return_value="frank/Autonomous_Forge"), \
             patch("autonomous_forge.doctor.ForgejoClient._request", return_value={"id": 1}):
            mock_git.return_value = MagicMock(returncode=0, stdout="git version 2.40.0")
            report = run_doctor(tmp_path)

        assert report.all_passed is True
        by_name = {c.name: c for c in report.checks}
        assert by_name["Forgejo repo reachable"].passed is True

    def test_repo_not_reachable_reports_hint(self, tmp_path: Path):
        _make_repo(tmp_path)
        with patch("autonomous_forge.doctor.subprocess.run") as mock_git, \
             patch("autonomous_forge.doctor._load_token", return_value="tok"), \
             patch("autonomous_forge.doctor._detect_forgejo_repo", return_value="frank/Autonomous-Forge"), \
             patch(
                 "autonomous_forge.doctor.ForgejoClient._request",
                 side_effect=RuntimeError("Forgejo API GET  returned 404: not found"),
             ):
            mock_git.return_value = MagicMock(returncode=0, stdout="git version 2.40.0")
            report = run_doctor(tmp_path)

        assert report.all_passed is False
        by_name = {c.name: c for c in report.checks}
        check = by_name["Forgejo repo reachable"]
        assert check.passed is False
        assert "renamed" in check.hint

    def test_git_not_found(self, tmp_path: Path):
        _make_repo(tmp_path)
        with patch("autonomous_forge.doctor.subprocess.run", side_effect=FileNotFoundError()), \
             patch("autonomous_forge.doctor._load_token", return_value="tok"), \
             patch("autonomous_forge.doctor._detect_forgejo_repo", return_value="frank/Autonomous_Forge"), \
             patch("autonomous_forge.doctor.ForgejoClient._request", return_value={"id": 1}):
            report = run_doctor(tmp_path)

        by_name = {c.name: c for c in report.checks}
        assert by_name["git available"].passed is False
        assert report.all_passed is False

    def test_repo_override_used_instead_of_detection(self, tmp_path: Path):
        _make_repo(tmp_path)
        with patch("autonomous_forge.doctor.subprocess.run") as mock_git, \
             patch("autonomous_forge.doctor._load_token", return_value="tok"), \
             patch("autonomous_forge.doctor._detect_forgejo_repo", return_value=None) as mock_detect, \
             patch("autonomous_forge.doctor.ForgejoClient._request", return_value={"id": 1}):
            mock_git.return_value = MagicMock(returncode=0, stdout="git version 2.40.0")
            report = run_doctor(tmp_path, repo_override="frank/Explicit-Repo")

        mock_detect.assert_not_called()
        by_name = {c.name: c for c in report.checks}
        assert by_name["Forgejo remote detected"].passed is True
        assert by_name["Forgejo remote detected"].message == "frank/Explicit-Repo"
