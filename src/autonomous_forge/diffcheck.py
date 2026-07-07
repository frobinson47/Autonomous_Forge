"""Validate changed files against repository policy boundaries."""

from __future__ import annotations

import fnmatch
import subprocess
from dataclasses import dataclass
from pathlib import Path

from autonomous_forge.policy import PolicyParseError, parse_repository_policy


@dataclass(frozen=True)
class DiffViolation:
    """A file change that violates policy boundaries."""

    path: str
    rule: str
    message: str


def _run_git(args: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def get_changed_files(root: Path, staged_only: bool = False) -> list[str]:
    """Get list of changed files from git diff."""
    if staged_only:
        output = _run_git(["diff", "--cached", "--name-only"], root)
    else:
        staged = _run_git(["diff", "--cached", "--name-only"], root)
        unstaged = _run_git(["diff", "--name-only"], root)
        untracked = _run_git(["ls-files", "--others", "--exclude-standard"], root)
        all_files = set()
        for block in (staged, unstaged, untracked):
            for line in block.splitlines():
                if line.strip():
                    all_files.add(line.strip())
        return sorted(all_files)
    return [f.strip() for f in output.splitlines() if f.strip()]


def _matches_pattern(filepath: str, pattern: str) -> bool:
    """Check if a filepath matches a glob-style policy pattern."""
    if fnmatch.fnmatch(filepath, pattern):
        return True
    parts = filepath.replace("\\", "/").split("/")
    for i in range(len(parts)):
        partial = "/".join(parts[i:])
        if fnmatch.fnmatch(partial, pattern):
            return True
    return False


def check_diff_against_policy(
    changed_files: list[str],
    policy_text: str,
) -> list[DiffViolation]:
    """Check changed files against policy allowed and prohibited paths."""
    try:
        policy = parse_repository_policy(policy_text)
    except PolicyParseError as exc:
        return [DiffViolation(
            path="(policy)",
            rule="parse",
            message=f"Could not parse policy: {exc}",
        )]

    violations: list[DiffViolation] = []

    for filepath in changed_files:
        is_prohibited = False
        for pattern in policy.prohibited_paths:
            if _matches_pattern(filepath, pattern):
                violations.append(DiffViolation(
                    path=filepath,
                    rule="prohibited",
                    message=f"Matches prohibited pattern '{pattern}'",
                ))
                is_prohibited = True
                break

        if not is_prohibited:
            allowed = any(
                _matches_pattern(filepath, pattern)
                for pattern in policy.allowed_paths
            )
            if not allowed:
                violations.append(DiffViolation(
                    path=filepath,
                    rule="not-allowed",
                    message="Not covered by any allowed path pattern",
                ))

    return violations


def build_diff_report(
    changed_files: list[str],
    policy_text: str | None,
) -> str:
    """Build a human-readable diff-check report."""
    lines = [
        "Diff check report",
        "Mode: read-only",
    ]

    if not changed_files:
        lines.append("Changed files: 0")
        lines.append("Result: nothing to check")
        return "\n".join(lines)

    lines.append(f"Changed files: {len(changed_files)}")

    if policy_text is None:
        lines.append("Policy: not found — cannot validate")
        lines.append("Changed files:")
        for f in changed_files:
            lines.append(f"  {f}")
        return "\n".join(lines)

    violations = check_diff_against_policy(changed_files, policy_text)

    if not violations:
        lines.append("Result: all changes comply with policy")
    else:
        lines.append(f"Result: {len(violations)} violation(s)")
        for v in violations:
            lines.append(f"  [{v.rule}] {v.path}: {v.message}")

    return "\n".join(lines)


def read_diff_report(
    root: Path = Path("."),
    policy_path: Path | None = None,
    staged_only: bool = False,
) -> str:
    """Read git diff and policy, then build a diff-check report."""
    pol_path = policy_path or (root / ".forge/policy.md")
    policy_text = pol_path.read_text(encoding="utf-8") if pol_path.exists() else None
    changed_files = get_changed_files(root, staged_only=staged_only)
    return build_diff_report(changed_files, policy_text)
