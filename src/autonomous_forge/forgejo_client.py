"""Forgejo HTTP transport: repo/token detection and a minimal API client."""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


def _detect_forgejo_repo(root: Path) -> str | None:
    """Extract owner/repo from the git remote URL."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, cwd=root, timeout=10,
        )
        url = result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return None

    match = re.search(r"forgejo\.familytechlab\.com[/:](.+?)(?:\.git)?$", url)
    if match:
        return match.group(1)
    return None


def _load_token() -> str | None:
    """Load Forgejo token from environment or .secrets.env."""
    token = os.environ.get("FORGEJO_TOKEN")
    if token:
        return token

    secrets_path = Path.home() / ".claude" / ".secrets.env"
    if secrets_path.exists():
        for line in secrets_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("FORGEJO_TOKEN="):
                val = line.split("=", 1)[1].strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                return val
    return None


class ForgejoClient:
    """Minimal Forgejo API client using only stdlib."""

    def __init__(self, repo: str, token: str):
        self.base = f"https://forgejo.familytechlab.com/api/v1/repos/{repo}"
        self.token = token

    def _request(
        self, method: str, path: str, data: dict | None = None
    ) -> dict | list | None:
        url = f"{self.base}{path}"
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={
                "Authorization": f"token {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode() if exc.fp else ""
            raise RuntimeError(
                f"Forgejo API {method} {path} returned {exc.code}: {error_body}"
            ) from exc

    def list_issues(self, state: str = "all", limit: int = 50) -> list[dict]:
        page = 1
        all_issues: list[dict] = []
        while True:
            issues = self._request(
                "GET", f"/issues?state={state}&type=issues&limit={limit}&page={page}"
            )
            if not issues:
                break
            all_issues.extend(issues)
            if len(issues) < limit:
                break
            page += 1
        return all_issues

    def create_issue(self, title: str, body: str, labels: list[int] | None = None,
                     milestone: int | None = None) -> dict:
        data: dict = {"title": title, "body": body}
        if labels:
            data["labels"] = labels
        if milestone:
            data["milestone"] = milestone
        return self._request("POST", "/issues", data)

    def update_issue(self, number: int, **kwargs) -> dict:
        return self._request("PATCH", f"/issues/{number}", kwargs)

    def add_comment(self, number: int, body: str) -> dict:
        return self._request("POST", f"/issues/{number}/comments", {"body": body})

    def list_labels(self) -> list[dict]:
        return self._request("GET", "/labels?limit=50") or []

    def create_label(self, name: str, color: str) -> dict:
        return self._request("POST", "/labels", {"name": name, "color": color})

    def list_milestones(self, state: str = "all") -> list[dict]:
        return self._request("GET", f"/milestones?state={state}&limit=50") or []

    def create_milestone(self, title: str) -> dict:
        return self._request("POST", "/milestones", {"title": title})

    def replace_labels(self, issue_number: int, label_ids: list[int]) -> list[dict]:
        return self._request("PUT", f"/issues/{issue_number}/labels", {"labels": label_ids})
