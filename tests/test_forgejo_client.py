"""Tests for the Forgejo HTTP transport (repo/token detection, API client)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from autonomous_forge.forgejo_client import _detect_forgejo_repo


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
