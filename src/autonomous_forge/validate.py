"""Run validation commands and record results."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from autonomous_forge.policy import PolicyParseError, parse_repository_policy


_DEFAULT_COMMAND = "python -m pytest"


@dataclass(frozen=True)
class ValidationResult:
    """Result of running a validation command."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    passed: bool
    timestamp: str


def _extract_validation_command(policy_text: str | None) -> str:
    """Try to extract a validation command from policy expectations."""
    if policy_text is None:
        return _DEFAULT_COMMAND
    try:
        policy = parse_repository_policy(policy_text)
    except PolicyParseError:
        return _DEFAULT_COMMAND
    for expectation in policy.validation_expectations:
        if expectation.startswith("Run `") and "`" in expectation[5:]:
            cmd = expectation[5:expectation.index("`", 5)]
            if cmd.strip():
                return cmd.strip()
    return _DEFAULT_COMMAND


def run_validation(
    root: Path = Path("."),
    command: str | None = None,
    policy_path: Path | None = None,
    timeout_seconds: int = 300,
    timestamp: str | None = None,
) -> ValidationResult:
    """Run a validation command and return structured results."""
    pol_path = policy_path or (root / ".forge/policy.md")
    policy_text = pol_path.read_text(encoding="utf-8") if pol_path.exists() else None
    cmd = command or _extract_validation_command(policy_text)
    ts = timestamp or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    env = os.environ.copy()
    if "PYTHONPATH=src " in cmd or cmd.startswith("PYTHONPATH=src "):
        env["PYTHONPATH"] = str(root / "src")
        cmd = cmd.replace("PYTHONPATH=src ", "", 1)

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=env,
        )
        return ValidationResult(
            command=cmd,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            passed=result.returncode == 0,
            timestamp=ts,
        )
    except subprocess.TimeoutExpired:
        return ValidationResult(
            command=cmd,
            exit_code=-1,
            stdout="",
            stderr=f"Command timed out after {timeout_seconds} seconds",
            passed=False,
            timestamp=ts,
        )
    except FileNotFoundError:
        return ValidationResult(
            command=cmd,
            exit_code=-1,
            stdout="",
            stderr="Command not found",
            passed=False,
            timestamp=ts,
        )


def format_validation_result(result: ValidationResult) -> str:
    """Format a validation result as a human-readable report."""
    status = "PASSED" if result.passed else "FAILED"
    lines = [
        "Validation report",
        f"Command: {result.command}",
        f"Result: {status}",
        f"Exit code: {result.exit_code}",
        f"Timestamp: {result.timestamp}",
    ]

    stdout_trimmed = result.stdout.strip()
    if stdout_trimmed:
        output_lines = stdout_trimmed.splitlines()
        if len(output_lines) > 20:
            lines.append("Output (last 20 lines):")
            for line in output_lines[-20:]:
                lines.append(f"  {line}")
        else:
            lines.append("Output:")
            for line in output_lines:
                lines.append(f"  {line}")

    stderr_trimmed = result.stderr.strip()
    if stderr_trimmed:
        stderr_lines = stderr_trimmed.splitlines()
        if len(stderr_lines) > 10:
            lines.append("Errors (last 10 lines):")
            for line in stderr_lines[-10:]:
                lines.append(f"  {line}")
        else:
            lines.append("Errors:")
            for line in stderr_lines:
                lines.append(f"  {line}")

    return "\n".join(lines)
