"""Forge doctor — diagnose common environment issues before a run.

Read-only: every check inspects local files, runs `git` for informational
output, or makes a single GET call to Forgejo. Nothing is created, updated,
or fixed automatically.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from autonomous_forge.sync import ForgejoClient, _detect_forgejo_repo, _load_token


@dataclass(frozen=True)
class DoctorCheck:
    """One diagnostic check result.

    ``passed`` is ``True``/``False`` for a real pass/fail, or ``None`` when
    the check could not run (e.g. skipped because an earlier check already
    failed) — a skipped check does not fail the overall report.
    """

    name: str
    passed: bool | None
    message: str
    hint: str = ""


@dataclass(frozen=True)
class DoctorReport:
    """Combined result of all environment diagnostic checks."""

    checks: tuple[DoctorCheck, ...]

    @property
    def all_passed(self) -> bool:
        return all(c.passed is not False for c in self.checks)


def _check_git_available() -> DoctorCheck:
    try:
        result = subprocess.run(
            ["git", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return DoctorCheck("git available", True, result.stdout.strip())
        return DoctorCheck(
            "git available", False, "git exited non-zero",
            hint="Ensure git is installed and on PATH.",
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return DoctorCheck(
            "git available", False, "git command not found",
            hint="Install git and ensure it is on PATH.",
        )


def _check_plan_files_present(root: Path, plan_path: Path | None) -> DoctorCheck:
    plan = plan_path or root / ".ai" / "AUTONOMOUS_PLAN.md"
    if plan.exists():
        return DoctorCheck("plan file present", True, str(plan))
    return DoctorCheck(
        "plan file present", False, f"{plan} not found",
        hint="Run `forge init` to scaffold .ai/ metadata files.",
    )


def _check_policy_file_present(root: Path, policy_path: Path | None) -> DoctorCheck:
    policy = policy_path or root / ".forge" / "policy.md"
    if policy.exists():
        return DoctorCheck("policy file present", True, str(policy))
    return DoctorCheck(
        "policy file present", False, f"{policy} not found",
        hint="Run `forge init` to scaffold a default .forge/policy.md.",
    )


def _check_forgejo_token() -> tuple[DoctorCheck, str | None]:
    token = _load_token()
    if token:
        return DoctorCheck("Forgejo token present", True, "found"), token
    return (
        DoctorCheck(
            "Forgejo token present", False, "no token found",
            hint="Set FORGEJO_TOKEN in the environment or ~/.claude/.secrets.env.",
        ),
        None,
    )


def _check_forgejo_remote(root: Path, repo_override: str | None) -> tuple[DoctorCheck, str | None]:
    repo = repo_override or _detect_forgejo_repo(root)
    if repo:
        return DoctorCheck("Forgejo remote detected", True, repo), repo
    return (
        DoctorCheck(
            "Forgejo remote detected", False, "could not detect a Forgejo remote",
            hint="Check `git remote -v` — origin should point at forgejo.familytechlab.com.",
        ),
        None,
    )


def _check_forgejo_repo_reachable(repo: str | None, token: str | None) -> DoctorCheck:
    if not repo or not token:
        return DoctorCheck(
            "Forgejo repo reachable", None,
            "skipped (needs a detected remote and token)",
        )
    client = ForgejoClient(repo, token)
    try:
        client._request("GET", "")
        return DoctorCheck("Forgejo repo reachable", True, f"{repo} resolved")
    except RuntimeError as exc:
        return DoctorCheck(
            "Forgejo repo reachable", False, str(exc),
            hint=(
                "A 404 here often means the repo was renamed on Forgejo "
                "(e.g. hyphen vs underscore) but the git remote URL wasn't "
                "updated — check `git remote -v` against the Forgejo repo name."
            ),
        )


def run_doctor(
    root: Path = Path("."),
    plan_path: Path | None = None,
    policy_path: Path | None = None,
    repo_override: str | None = None,
    token_override: str | None = None,
) -> DoctorReport:
    """Run all environment diagnostic checks and return a combined report."""
    checks: list[DoctorCheck] = []

    checks.append(_check_git_available())
    checks.append(_check_plan_files_present(root, plan_path))
    checks.append(_check_policy_file_present(root, policy_path))

    token_check, token = _check_forgejo_token()
    if token_override:
        token = token_override
    checks.append(token_check)

    remote_check, repo = _check_forgejo_remote(root, repo_override)
    checks.append(remote_check)

    checks.append(_check_forgejo_repo_reachable(repo, token))

    return DoctorReport(checks=tuple(checks))


def format_doctor_report(report: DoctorReport) -> str:
    """Format a doctor report as a human-readable summary."""
    lines = ["Forge doctor"]
    for check in report.checks:
        if check.passed is True:
            status = "PASS"
        elif check.passed is False:
            status = "FAIL"
        else:
            status = "SKIP"
        lines.append(f"{check.name}: {status} — {check.message}")
        if check.passed is False and check.hint:
            lines.append(f"  hint: {check.hint}")
    lines.append(f"Result: {'ALL PASSED' if report.all_passed else 'ISSUES FOUND'}")
    return "\n".join(lines)
