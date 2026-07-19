"""Tests for the push-to-remote module."""

from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from autonomous_forge.push import PushResult, execute_push, format_push_result


def _proc(returncode: int, stdout: str = "", stderr: str = "") -> CompletedProcess:
    return CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class TestExecutePush:
    @patch("autonomous_forge.push.subprocess.run")
    def test_already_up_to_date_skips_push(self, mock_run, tmp_path):
        mock_run.side_effect = [
            _proc(0, stdout="main\n"),  # rev-parse --abbrev-ref HEAD
            _proc(0, stdout="0\n"),  # rev-list --count origin/main..HEAD
        ]
        result = execute_push(root=tmp_path)

        assert result.pushed
        assert result.commits_pushed == 0
        assert "up to date" in result.message
        assert mock_run.call_count == 2  # no push invoked

    @patch("autonomous_forge.push.subprocess.run")
    def test_pushes_when_ahead(self, mock_run, tmp_path):
        mock_run.side_effect = [
            _proc(0, stdout="main\n"),
            _proc(0, stdout="3\n"),
            _proc(0, stdout=""),  # git push
        ]
        result = execute_push(root=tmp_path)

        assert result.pushed
        assert result.commits_pushed == 3
        assert result.remote == "origin"
        assert result.branch == "main"
        assert "Pushed 3 commit(s)" in result.message

    @patch("autonomous_forge.push.subprocess.run")
    def test_push_rejected_fails_loudly(self, mock_run, tmp_path):
        mock_run.side_effect = [
            _proc(0, stdout="main\n"),
            _proc(0, stdout="1\n"),
            _proc(1, stderr="! [rejected] main -> main (non-fast-forward)"),
        ]
        result = execute_push(root=tmp_path)

        assert not result.pushed
        assert "rejected" in result.message
        assert result.commits_pushed == 0

    @patch("autonomous_forge.push.subprocess.run")
    def test_first_push_with_no_upstream_still_attempts_push(self, mock_run, tmp_path):
        mock_run.side_effect = [
            _proc(0, stdout="main\n"),
            _proc(128, stderr="unknown revision or path not in the working tree"),
            _proc(0, stdout=""),
        ]
        result = execute_push(root=tmp_path)

        assert result.pushed
        assert mock_run.call_count == 3

    @patch("autonomous_forge.push.subprocess.run")
    def test_branch_detection_failure(self, mock_run, tmp_path):
        mock_run.side_effect = [_proc(1, stderr="not a git repository")]
        result = execute_push(root=tmp_path)

        assert not result.pushed
        assert "Could not determine current branch" in result.message


class TestFormatPushResult:
    def test_pushed(self):
        result = PushResult(
            pushed=True, remote="origin", branch="main",
            commits_pushed=2, message="Pushed 2 commit(s) to origin/main.",
        )
        text = format_push_result(result)
        assert "PUSHED" in text
        assert "origin/main" in text

    def test_failed(self):
        result = PushResult(
            pushed=False, remote="origin", branch="main",
            commits_pushed=0, message="git push failed: rejected",
        )
        text = format_push_result(result)
        assert "FAILED" in text
