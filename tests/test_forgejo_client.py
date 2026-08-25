"""Tests for the Forgejo HTTP transport (repo/token detection, API client)."""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

from autonomous_forge.forgejo_client import (
    ForgejoClient,
    ForgejoConfigError,
    _detect_forgejo_repo,
    normalize_repo,
    resolve_base_url,
)


class TestDetectForgejoRepo:
    def test_detect_forgejo_repo(self, tmp_path: Path):
        with patch("autonomous_forge.forgejo_client.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="https://forgejo.familytechlab.com/frank/Autonomous-Forge.git\n"
            )
            result = _detect_forgejo_repo(tmp_path)
            assert result == "frank/Autonomous-Forge"

    def test_detect_forgejo_repo_non_forgejo(self, tmp_path: Path):
        with patch("autonomous_forge.forgejo_client.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="https://github.com/foo/bar.git\n")
            result = _detect_forgejo_repo(tmp_path)
            assert result is None

    def test_detect_forgejo_repo_custom_base_url(self, tmp_path: Path):
        with patch("autonomous_forge.forgejo_client.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="https://git.example.com/owner/repo.git\n"
            )
            result = _detect_forgejo_repo(tmp_path, base_url="https://git.example.com")
            assert result == "owner/repo"

    def test_detect_forgejo_repo_wrong_host_for_configured_base_url(self, tmp_path: Path):
        with patch("autonomous_forge.forgejo_client.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="https://forgejo.familytechlab.com/frank/repo.git\n"
            )
            result = _detect_forgejo_repo(tmp_path, base_url="https://git.example.com")
            assert result is None


class TestResolveBaseUrl:
    def test_default_when_nothing_configured(self, tmp_path: Path):
        assert resolve_base_url(tmp_path) == "https://forgejo.familytechlab.com"

    def test_explicit_override_wins(self, tmp_path: Path):
        assert resolve_base_url(tmp_path, "https://git.example.com") == "https://git.example.com"

    def test_override_strips_trailing_slash(self, tmp_path: Path):
        assert resolve_base_url(tmp_path, "https://git.example.com/") == "https://git.example.com"

    def test_env_var_used_when_no_override(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("FORGEJO_BASE_URL", "https://from-env.example.com")
        assert resolve_base_url(tmp_path) == "https://from-env.example.com"

    def test_config_file_used_when_no_override_or_env(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv("FORGEJO_BASE_URL", raising=False)
        (tmp_path / ".forge").mkdir()
        (tmp_path / ".forge" / "config.toml").write_text(
            '[defaults]\nforgejo_base_url = "https://from-config.example.com"\n',
            encoding="utf-8",
        )
        assert resolve_base_url(tmp_path) == "https://from-config.example.com"

    def test_rejects_non_https(self, tmp_path: Path):
        try:
            resolve_base_url(tmp_path, "http://insecure.example.com")
        except ForgejoConfigError:
            pass
        else:
            raise AssertionError("expected ForgejoConfigError for non-https URL")

    def test_rejects_malformed_url(self, tmp_path: Path):
        try:
            resolve_base_url(tmp_path, "not a url")
        except ForgejoConfigError:
            pass
        else:
            raise AssertionError("expected ForgejoConfigError for malformed URL")


class TestNormalizeRepo:
    def test_valid_repo_unchanged(self):
        assert normalize_repo("owner/repo") == "owner/repo"

    def test_strips_surrounding_slashes_and_whitespace(self):
        assert normalize_repo("  /owner/repo/  ") == "owner/repo"

    def test_rejects_missing_slash(self):
        assert normalize_repo("owner-repo") is None

    def test_rejects_extra_path_segments(self):
        assert normalize_repo("owner/repo/extra") is None

    def test_rejects_shell_metacharacters(self):
        assert normalize_repo("owner/repo; rm -rf /") is None


class TestForgejoClientRequest:
    def test_uses_configured_base_url(self):
        client = ForgejoClient("owner/repo", "tok", base_url="https://git.example.com")
        assert client.base == "https://git.example.com/api/v1/repos/owner/repo"

    def test_refuses_non_https_url_at_request_time(self):
        # Defense in depth (AUTO-072 / S310): even if ForgejoClient is
        # constructed directly with an unvalidated base_url (bypassing
        # resolve_base_url's own https-only check), _request must still
        # refuse rather than open a non-https connection.
        client = ForgejoClient("owner/repo", "tok", base_url="http://insecure.example.com")
        try:
            client.list_labels()
        except RuntimeError as exc:
            assert "non-https" in str(exc).lower()
        else:
            raise AssertionError("expected RuntimeError for a non-https URL")

    def test_defaults_to_project_instance(self):
        client = ForgejoClient("owner/repo", "tok")
        assert client.base == "https://forgejo.familytechlab.com/api/v1/repos/owner/repo"

    @patch("autonomous_forge.forgejo_client.urllib.request.urlopen")
    def test_url_error_becomes_runtime_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Name or service not known")
        client = ForgejoClient("owner/repo", "tok")
        try:
            client.list_labels()
        except RuntimeError as exc:
            assert "could not connect" in str(exc).lower()
        else:
            raise AssertionError("expected RuntimeError, not a raw URLError")

    @patch("autonomous_forge.forgejo_client.urllib.request.urlopen")
    def test_timeout_becomes_runtime_error(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("timed out")
        client = ForgejoClient("owner/repo", "tok")
        try:
            client.list_labels()
        except RuntimeError as exc:
            assert "timed out" in str(exc).lower()
        else:
            raise AssertionError("expected RuntimeError, not a raw TimeoutError")

    @patch("autonomous_forge.forgejo_client.urllib.request.urlopen")
    def test_malformed_json_becomes_runtime_error(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b"not json{{{"
        mock_urlopen.return_value.__enter__.return_value = mock_response
        client = ForgejoClient("owner/repo", "tok")
        try:
            client.list_labels()
        except RuntimeError as exc:
            assert "malformed json" in str(exc).lower()
        except json.JSONDecodeError:
            raise AssertionError("raw JSONDecodeError leaked instead of RuntimeError")
        else:
            raise AssertionError("expected RuntimeError for malformed JSON")


def _set_response_body(mock_urlopen: MagicMock, body: bytes) -> None:
    """Configure a mocked urlopen() to return the given raw response body."""
    mock_response = MagicMock()
    mock_response.read.return_value = body
    mock_urlopen.return_value.__enter__.return_value = mock_response


class TestForgejoClientResponseShapeValidation:
    """AUTO-073: a schema-conformant-but-wrong response must raise a clean
    RuntimeError, not a raw KeyError/TypeError once a caller indexes into it."""

    @patch("autonomous_forge.forgejo_client.urllib.request.urlopen")
    def test_list_issues_rejects_dict_instead_of_array(self, mock_urlopen):
        _set_response_body(mock_urlopen, json.dumps({"message": "not an array"}).encode())
        try:
            ForgejoClient("owner/repo", "tok").list_issues()
        except RuntimeError as exc:
            assert "expected an array" in str(exc).lower()
        else:
            raise AssertionError("expected RuntimeError for a dict where an array was expected")

    @patch("autonomous_forge.forgejo_client.urllib.request.urlopen")
    def test_list_issues_rejects_array_of_non_dicts(self, mock_urlopen):
        _set_response_body(mock_urlopen, json.dumps(["not", "objects"]).encode())
        try:
            ForgejoClient("owner/repo", "tok").list_issues()
        except RuntimeError as exc:
            assert "expected an object" in str(exc).lower()
        else:
            raise AssertionError("expected RuntimeError for an array of non-objects")

    @patch("autonomous_forge.forgejo_client.urllib.request.urlopen")
    def test_create_issue_rejects_response_missing_number(self, mock_urlopen):
        _set_response_body(mock_urlopen, json.dumps({"title": "x"}).encode())
        try:
            ForgejoClient("owner/repo", "tok").create_issue("title", "body")
        except RuntimeError as exc:
            assert "number" in str(exc).lower()
        else:
            raise AssertionError("expected RuntimeError for a response missing 'number'")

    @patch("autonomous_forge.forgejo_client.urllib.request.urlopen")
    def test_create_issue_rejects_array_instead_of_object(self, mock_urlopen):
        _set_response_body(mock_urlopen, json.dumps([1, 2, 3]).encode())
        try:
            ForgejoClient("owner/repo", "tok").create_issue("title", "body")
        except RuntimeError as exc:
            assert "expected an object" in str(exc).lower()
        else:
            raise AssertionError("expected RuntimeError for an array where an object was expected")

    @patch("autonomous_forge.forgejo_client.urllib.request.urlopen")
    def test_list_labels_rejects_item_missing_required_key(self, mock_urlopen):
        _set_response_body(mock_urlopen, json.dumps([{"id": 1}]).encode())  # missing "name"
        try:
            ForgejoClient("owner/repo", "tok").list_labels()
        except RuntimeError as exc:
            assert "name" in str(exc).lower()
        else:
            raise AssertionError("expected RuntimeError for a label missing 'name'")

    @patch("autonomous_forge.forgejo_client.urllib.request.urlopen")
    def test_create_label_accepts_well_formed_response(self, mock_urlopen):
        _set_response_body(
            mock_urlopen, json.dumps({"id": 5, "name": "bug", "color": "#ff0000"}).encode()
        )
        result = ForgejoClient("owner/repo", "tok").create_label("bug", "#ff0000")
        assert result["id"] == 5

    @patch("autonomous_forge.forgejo_client.urllib.request.urlopen")
    def test_list_milestones_accepts_well_formed_response(self, mock_urlopen):
        _set_response_body(mock_urlopen, json.dumps([{"id": 1, "title": "v1"}]).encode())
        result = ForgejoClient("owner/repo", "tok").list_milestones()
        assert result[0]["title"] == "v1"
