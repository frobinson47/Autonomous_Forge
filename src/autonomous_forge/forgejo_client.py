"""Forgejo HTTP transport: repo/token detection and a minimal API client."""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import cast

from autonomous_forge.config import load_config

_DEFAULT_BASE_URL = "https://forgejo.familytechlab.com"
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class ForgejoConfigError(ValueError):
    """Raised when a configured Forgejo base URL or repo name is invalid."""


def _validate_base_url(url: str) -> str:
    """Require a well-formed https:// URL; strip any trailing slash."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ForgejoConfigError(
            f"Forgejo base URL must be a well-formed https:// URL, got: {url!r}"
        )
    return url.rstrip("/")


def resolve_base_url(root: Path = Path("."), override: str | None = None) -> str:
    """Resolve the Forgejo base URL.

    Precedence: explicit ``override`` > ``FORGEJO_BASE_URL`` environment
    variable > ``.forge/config.toml``'s ``forgejo_base_url`` default >
    this project's own Forgejo instance (unchanged default behavior for
    existing repos that configure nothing).
    """
    if override:
        return _validate_base_url(override)
    env_url = os.environ.get("FORGEJO_BASE_URL")
    if env_url:
        return _validate_base_url(env_url)
    config_url = load_config(root).forgejo_base_url
    if config_url:
        return _validate_base_url(config_url)
    return _DEFAULT_BASE_URL


def normalize_repo(repo: str) -> str | None:
    """Return a validated ``owner/repo`` string, or None if malformed."""
    repo = repo.strip().strip("/")
    return repo if _REPO_RE.match(repo) else None


def _detect_forgejo_repo(root: Path, base_url: str = _DEFAULT_BASE_URL) -> str | None:
    """Extract owner/repo from the git remote URL, matching base_url's host."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],  # noqa: S607 — "git" via PATH is intentional
            capture_output=True, text=True, cwd=root, timeout=10,
        )
        url = result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return None

    host = urllib.parse.urlparse(base_url).netloc
    if not host:
        return None
    match = re.search(rf"{re.escape(host)}[/:](.+?)(?:\.git)?$", url)
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

    def __init__(self, repo: str, token: str, base_url: str = _DEFAULT_BASE_URL):
        self.base = f"{base_url}/api/v1/repos/{repo}"
        self.token = token

    def _request(
        self, method: str, path: str, data: dict | None = None
    ) -> dict | list | None:
        url = f"{self.base}{path}"
        # Re-checked here, not just trusted from resolve_base_url's caller-side
        # validation (AUTO-067) — this is the one place that actually opens
        # the connection, so it's the right place for the guarantee to hold
        # regardless of how ForgejoClient was constructed (AUTO-072 / S310).
        if not url.startswith("https://"):
            raise RuntimeError(f"Refusing to request a non-https URL: {url}")
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(  # noqa: S310 — scheme checked immediately above
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
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 — see above
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode() if exc.fp else ""
            raise RuntimeError(
                f"Forgejo API {method} {path} returned {exc.code}: {error_body}"
            ) from exc
        except TimeoutError as exc:
            raise RuntimeError(f"Forgejo API {method} {path} timed out") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Forgejo API {method} {path} could not connect: {exc.reason}"
            ) from exc

        try:
            return json.loads(raw.decode())
        except UnicodeDecodeError as exc:
            raise RuntimeError(
                f"Forgejo API {method} {path} returned an undecodable response: {exc}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Forgejo API {method} {path} returned malformed JSON: {exc}"
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
        # _request's return type is intentionally loose (mirrors arbitrary
        # JSON) — these casts assert the documented shape of each specific
        # Forgejo endpoint, which the API contract guarantees but the
        # generic _request signature can't express.
        return cast(dict, self._request("POST", "/issues", data))

    def update_issue(self, number: int, **kwargs) -> dict:
        return cast(dict, self._request("PATCH", f"/issues/{number}", kwargs))

    def add_comment(self, number: int, body: str) -> dict:
        return cast(dict, self._request("POST", f"/issues/{number}/comments", {"body": body}))

    def list_labels(self) -> list[dict]:
        return cast(list, self._request("GET", "/labels?limit=50")) or []

    def create_label(self, name: str, color: str) -> dict:
        return cast(dict, self._request("POST", "/labels", {"name": name, "color": color}))

    def list_milestones(self, state: str = "all") -> list[dict]:
        return cast(list, self._request("GET", f"/milestones?state={state}&limit=50")) or []

    def create_milestone(self, title: str) -> dict:
        return cast(dict, self._request("POST", "/milestones", {"title": title}))

    def replace_labels(self, issue_number: int, label_ids: list[int]) -> list[dict]:
        return cast(
            list, self._request("PUT", f"/issues/{issue_number}/labels", {"labels": label_ids})
        )
