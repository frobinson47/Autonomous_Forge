"""Tests for error and fallback branches in status, validate and forgejo_client (AUTO-078).

These branches only run when something goes wrong (git missing, a command
that times out, a malformed API reply), so the happy-path suites never
reached them.
"""

from __future__ import annotations

import io
import subprocess
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from autonomous_forge.forgejo_client import (
    ForgejoClient,
    _detect_forgejo_repo,
    _load_token,
)
from autonomous_forge.status import _git_branch, _git_dirty_count, _last_run_summary
from autonomous_forge.validate import (
    ValidationResult,
    _extract_validation_command,
    format_validation_result,
    run_validation,
)

TS = "2026-11-15T12:00:00+00:00"


def _completed(returncode: int = 0, stdout: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


# --- status.py -------------------------------------------------------------


class TestStatusGitHelpers:
    def test_branch_name_is_stripped(self, tmp_path):
        with patch("autonomous_forge.status.subprocess.run", return_value=_completed(0, "main\n")):
            assert _git_branch(tmp_path) == "main"

    def test_branch_unknown_on_nonzero_exit(self, tmp_path):
        with patch("autonomous_forge.status.subprocess.run", return_value=_completed(128)):
            assert _git_branch(tmp_path) == "unknown"

    def test_branch_unknown_when_git_is_missing(self, tmp_path):
        with patch("autonomous_forge.status.subprocess.run", side_effect=FileNotFoundError):
            assert _git_branch(tmp_path) == "unknown"

    def test_branch_unknown_on_timeout(self, tmp_path):
        err = subprocess.TimeoutExpired(cmd="git", timeout=5)
        with patch("autonomous_forge.status.subprocess.run", side_effect=err):
            assert _git_branch(tmp_path) == "unknown"

    def test_dirty_count_ignores_blank_lines(self, tmp_path):
        out = " M a.py\n?? b.py\n\n   \n"
        with patch("autonomous_forge.status.subprocess.run", return_value=_completed(0, out)):
            assert _git_dirty_count(tmp_path) == 2

    def test_dirty_count_is_minus_one_on_nonzero_exit(self, tmp_path):
        with patch("autonomous_forge.status.subprocess.run", return_value=_completed(128)):
            assert _git_dirty_count(tmp_path) == -1

    def test_dirty_count_is_minus_one_when_git_is_missing(self, tmp_path):
        with patch("autonomous_forge.status.subprocess.run", side_effect=FileNotFoundError):
            assert _git_dirty_count(tmp_path) == -1

    def test_dirty_count_is_minus_one_on_timeout(self, tmp_path):
        err = subprocess.TimeoutExpired(cmd="git", timeout=5)
        with patch("autonomous_forge.status.subprocess.run", side_effect=err):
            assert _git_dirty_count(tmp_path) == -1


class TestLastRunSummary:
    def test_empty_when_no_runs_directory(self, tmp_path):
        assert _last_run_summary(tmp_path) == ""

    def test_empty_when_runs_directory_has_no_run_files(self, tmp_path):
        (tmp_path / ".forge" / "runs").mkdir(parents=True)
        (tmp_path / ".forge" / "runs" / "notes.txt").write_text("x", encoding="utf-8")
        assert _last_run_summary(tmp_path) == ""

    def test_returns_timestamp_of_the_newest_run(self, tmp_path):
        runs = tmp_path / ".forge" / "runs"
        runs.mkdir(parents=True)
        for name in ("run-2026-11-01_10-00-00.md", "run-2026-11-09_14-00-00.md"):
            (runs / name).write_text("x", encoding="utf-8")
        assert _last_run_summary(tmp_path) == "2026-11-09_14-00-00"


# --- validate.py -----------------------------------------------------------


def _policy(*expectations: str) -> str:
    bullets = "\n".join(f"- {e}" for e in expectations) or "- placeholder"
    return (
        "# Policy\n\n## Allowed paths\n\n- `src/**`\n\n## Prohibited paths\n\n- `.env`\n\n"
        "## Human approval required\n\n- Anything risky.\n\n"
        f"## Validation expectations\n\n{bullets}\n"
    )


class TestExtractValidationCommand:
    def test_default_when_there_is_no_policy(self):
        assert _extract_validation_command(None) == "python -m pytest"

    def test_default_when_policy_cannot_be_parsed(self):
        assert _extract_validation_command("not a policy at all") == "python -m pytest"

    def test_uses_the_command_in_backticks(self):
        text = _policy("Run targeted tests.", "Run `make check` before committing.")
        assert _extract_validation_command(text) == "make check"

    def test_first_run_expectation_wins(self):
        text = _policy("Run `first cmd` now.", "Run `second cmd` later.")
        assert _extract_validation_command(text) == "first cmd"

    def test_default_when_backticks_are_empty(self):
        text = _policy("Run `  ` before committing.")
        assert _extract_validation_command(text) == "python -m pytest"

    def test_default_when_no_expectation_names_a_command(self):
        text = _policy("Be careful.")
        assert _extract_validation_command(text) == "python -m pytest"

    def test_run_validation_reads_the_command_from_the_policy_file(self, tmp_path):
        forge = tmp_path / ".forge"
        forge.mkdir()
        (forge / "policy.md").write_text(_policy("Run `python -c pass` always."), encoding="utf-8")
        result = run_validation(tmp_path, timestamp=TS)
        assert result.command == "python -c pass"
        assert result.passed is True


class TestRunValidationFailures:
    def test_command_not_found_is_a_failed_result_not_a_crash(self, tmp_path):
        result = run_validation(tmp_path, command="forge-no-such-binary-xyz --flag", timestamp=TS)
        assert result.passed is False
        assert result.exit_code == -1
        assert result.stderr == "Command not found"

    def test_unbalanced_quote_is_reported_as_a_parse_error(self, tmp_path):
        result = run_validation(tmp_path, command='python -c "unterminated', timestamp=TS)
        assert result.passed is False
        assert result.exit_code == -1
        assert result.stderr.startswith("Could not parse command:")

    def test_pythonpath_src_prefix_is_moved_into_the_environment(self, tmp_path):
        with patch("autonomous_forge.validate.subprocess.run") as run:
            run.return_value = _completed(0, "ok")
            result = run_validation(
                tmp_path, command="PYTHONPATH=src python -m pytest -q", timestamp=TS
            )
        assert result.command == "python -m pytest -q"
        assert run.call_args.args[0] == ["python", "-m", "pytest", "-q"]
        assert run.call_args.kwargs["env"]["PYTHONPATH"] == str(tmp_path / "src")
        assert result.passed is True


class TestFormatValidationResultTruncation:
    def _result(self, stdout: str = "", stderr: str = "") -> ValidationResult:
        return ValidationResult(
            command="x", exit_code=1, stdout=stdout, stderr=stderr, passed=False, timestamp=TS
        )

    def test_long_stdout_keeps_only_the_last_20_lines(self):
        stdout = "\n".join(f"out{i}" for i in range(30))
        text = format_validation_result(self._result(stdout=stdout))
        assert "Output (last 20 lines):" in text
        assert "out29" in text
        assert "out10" in text
        assert "out9" not in text.replace("out29", "")

    def test_long_stderr_keeps_only_the_last_10_lines(self):
        stderr = "\n".join(f"err{i}" for i in range(15))
        text = format_validation_result(self._result(stderr=stderr))
        assert "Errors (last 10 lines):" in text
        assert "err14" in text
        assert "err5" in text
        assert "err4" not in text

    def test_short_output_is_shown_in_full(self):
        text = format_validation_result(self._result(stdout="a\nb", stderr="e"))
        assert "Output:" in text
        assert "Errors:" in text
        assert "last 20" not in text
        assert "last 10" not in text


# --- forgejo_client.py -----------------------------------------------------


def _urlopen_returning(raw: bytes) -> MagicMock:
    response = MagicMock()
    response.read.return_value = raw
    response.__enter__.return_value = response
    return response


class TestRequestErrors:
    def test_http_error_includes_status_and_body(self):
        err = urllib.error.HTTPError(
            "https://x/api", 403, "Forbidden", {}, io.BytesIO(b"no access")
        )
        with patch("autonomous_forge.forgejo_client.urllib.request.urlopen", side_effect=err):
            with pytest.raises(RuntimeError) as exc:
                ForgejoClient("o/r", "tok", base_url="https://x").list_labels()
        assert "returned 403" in str(exc.value)
        assert "no access" in str(exc.value)

    def test_http_error_without_a_body_still_raises_cleanly(self):
        err = urllib.error.HTTPError("https://x/api", 500, "Server Error", {}, None)
        with patch("autonomous_forge.forgejo_client.urllib.request.urlopen", side_effect=err):
            with pytest.raises(RuntimeError) as exc:
                ForgejoClient("o/r", "tok", base_url="https://x").list_labels()
        assert "returned 500" in str(exc.value)

    def test_undecodable_response_becomes_runtime_error(self):
        resp = _urlopen_returning(b"\xff\xfe\x00bad")
        with patch("autonomous_forge.forgejo_client.urllib.request.urlopen", return_value=resp):
            with pytest.raises(RuntimeError) as exc:
                ForgejoClient("o/r", "tok", base_url="https://x").list_labels()
        assert "undecodable" in str(exc.value)


class TestClientMethods:
    def _client(self) -> ForgejoClient:
        return ForgejoClient("o/r", "tok", base_url="https://x")

    def test_list_issues_pages_until_a_short_page(self):
        full = [{"number": i} for i in range(2)]
        last = [{"number": 2}]
        with patch.object(ForgejoClient, "_request", side_effect=[full, last]) as req:
            issues = self._client().list_issues(limit=2)
        assert [i["number"] for i in issues] == [0, 1, 2]
        assert req.call_count == 2
        assert "page=2" in req.call_args.args[1]

    def test_list_issues_stops_on_an_empty_page(self):
        with patch.object(ForgejoClient, "_request", return_value=[]):
            assert self._client().list_issues() == []

    def test_list_labels_and_milestones_treat_an_empty_reply_as_none(self):
        with patch.object(ForgejoClient, "_request", return_value=None):
            assert self._client().list_labels() == []
            assert self._client().list_milestones() == []

    def test_create_issue_sends_labels_and_milestone_only_when_given(self):
        with patch.object(ForgejoClient, "_request", return_value={"number": 1}) as req:
            self._client().create_issue("t", "b")
            self._client().create_issue("t", "b", labels=[1, 2], milestone=3)
        assert req.call_args_list[0].args[2] == {"title": "t", "body": "b"}
        assert req.call_args_list[1].args[2] == {
            "title": "t", "body": "b", "labels": [1, 2], "milestone": 3,
        }

    def test_update_issue_comment_and_milestone_methods_use_the_right_endpoints(self):
        with patch.object(ForgejoClient, "_request", return_value={"id": 1}) as req:
            self._client().update_issue(5, state="closed")
            self._client().add_comment(5, "hi")
            self._client().create_milestone("Roadmap v1")
        calls = [(c.args[0], c.args[1]) for c in req.call_args_list]
        assert calls == [
            ("PATCH", "/issues/5"),
            ("POST", "/issues/5/comments"),
            ("POST", "/milestones"),
        ]

    def test_replace_labels_puts_the_label_ids(self):
        with patch.object(ForgejoClient, "_request", return_value=[{"id": 1}]) as req:
            self._client().replace_labels(5, [1, 2])
        assert req.call_args.args == ("PUT", "/issues/5/labels", {"labels": [1, 2]})

    def test_replace_labels_rejects_a_non_array_reply(self):
        with patch.object(ForgejoClient, "_request", return_value={"message": "no"}):
            with pytest.raises(RuntimeError, match="expected an array"):
                self._client().replace_labels(5, [1])

    def test_create_milestone_rejects_a_reply_without_an_id(self):
        with patch.object(ForgejoClient, "_request", return_value={"title": "x"}):
            with pytest.raises(RuntimeError, match="id"):
                self._client().create_milestone("x")


class TestRepoAndTokenDetection:
    def test_detect_repo_returns_none_when_git_fails(self, tmp_path):
        with patch(
            "autonomous_forge.forgejo_client.subprocess.run",
            side_effect=subprocess.SubprocessError,
        ):
            assert _detect_forgejo_repo(tmp_path) is None

    def test_detect_repo_returns_none_when_git_is_missing(self, tmp_path):
        with patch("autonomous_forge.forgejo_client.subprocess.run", side_effect=FileNotFoundError):
            assert _detect_forgejo_repo(tmp_path) is None

    def test_detect_repo_returns_none_for_a_base_url_without_a_host(self, tmp_path):
        with patch(
            "autonomous_forge.forgejo_client.subprocess.run",
            return_value=_completed(0, "https://forgejo.example/o/r.git\n"),
        ):
            assert _detect_forgejo_repo(tmp_path, base_url="not-a-url") is None

    def test_token_comes_from_the_environment_first(self, monkeypatch, tmp_path):
        monkeypatch.setenv("FORGEJO_TOKEN", "from-env")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert _load_token() == "from-env"

    @pytest.mark.parametrize(
        "line, expected",
        [
            ("FORGEJO_TOKEN=plain", "plain"),
            ('FORGEJO_TOKEN="double"', "double"),
            ("FORGEJO_TOKEN='single'", "single"),
            ("  FORGEJO_TOKEN=padded  ", "padded"),
        ],
    )
    def test_token_is_read_from_the_secrets_file(self, monkeypatch, tmp_path, line, expected):
        monkeypatch.delenv("FORGEJO_TOKEN", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        secrets = tmp_path / ".claude" / ".secrets.env"
        secrets.parent.mkdir()
        secrets.write_text(f"OTHER=1\n{line}\n", encoding="utf-8")
        assert _load_token() == expected

    def test_no_token_anywhere_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.delenv("FORGEJO_TOKEN", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert _load_token() is None

    def test_secrets_file_without_the_key_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.delenv("FORGEJO_TOKEN", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        secrets = tmp_path / ".claude" / ".secrets.env"
        secrets.parent.mkdir()
        secrets.write_text("SOMETHING_ELSE=1\n", encoding="utf-8")
        assert _load_token() is None

