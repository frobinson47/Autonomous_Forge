"""Push local commits to the git remote."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PushResult:
    """Result of a push attempt."""

    pushed: bool
    remote: str
    branch: str
    commits_pushed: int
    message: str


def _run_git(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git"] + args,
        capture_output=True, text=True, cwd=root, timeout=30,
    )


def execute_push(
    root: Path = Path("."),
    remote: str = "origin",
    branch: str | None = None,
) -> PushResult:
    """Push HEAD to the remote. Never rebases, merges, or force-pushes.

    Fails loudly (pushed=False) on any error, including a diverged/rejected
    push — the caller must resolve divergence manually before retrying.
    """
    branch_result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    if branch_result.returncode != 0:
        return PushResult(
            pushed=False,
            remote=remote,
            branch=branch or "",
            commits_pushed=0,
            message=f"Could not determine current branch: {branch_result.stderr.strip()}",
        )
    current_branch = branch or branch_result.stdout.strip()

    ahead_result = _run_git(
        ["rev-list", "--count", f"{remote}/{current_branch}..HEAD"], root,
    )
    commits_pushed = (
        int(ahead_result.stdout.strip())
        if ahead_result.returncode == 0 and ahead_result.stdout.strip().isdigit()
        else 0
    )

    if commits_pushed == 0 and ahead_result.returncode == 0:
        return PushResult(
            pushed=True,
            remote=remote,
            branch=current_branch,
            commits_pushed=0,
            message="Already up to date with remote.",
        )

    try:
        result = _run_git(["push", remote, current_branch], root)
    except subprocess.SubprocessError as exc:
        return PushResult(
            pushed=False,
            remote=remote,
            branch=current_branch,
            commits_pushed=0,
            message=f"git error: {exc}",
        )

    if result.returncode != 0:
        return PushResult(
            pushed=False,
            remote=remote,
            branch=current_branch,
            commits_pushed=0,
            message=f"git push failed: {result.stderr.strip()}",
        )

    return PushResult(
        pushed=True,
        remote=remote,
        branch=current_branch,
        commits_pushed=commits_pushed,
        message=f"Pushed {commits_pushed} commit(s) to {remote}/{current_branch}.",
    )


def format_push_result(result: PushResult) -> str:
    """Format a push result as a human-readable report."""
    status = "PUSHED" if result.pushed else "FAILED"
    return f"Push ({result.remote}/{result.branch}): {status} — {result.message}"
