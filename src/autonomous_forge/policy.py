"""Parse conservative Autonomous Forge repository policy files."""

from __future__ import annotations

from dataclasses import dataclass


_REQUIRED_SECTIONS = {
    "Allowed paths": "allowed_paths",
    "Prohibited paths": "prohibited_paths",
    "Human approval required": "approval_required",
    "Validation expectations": "validation_expectations",
}


@dataclass(frozen=True)
class RepositoryPolicy:
    """Structured summary of a repository policy file."""

    allowed_paths: tuple[str, ...]
    prohibited_paths: tuple[str, ...]
    approval_required: tuple[str, ...]
    validation_expectations: tuple[str, ...]


class PolicyParseError(ValueError):
    """Raised when a repository policy file is missing required structure."""


def parse_repository_policy(policy_text: str) -> RepositoryPolicy:
    """Parse the documented Markdown policy format into a structured summary."""
    sections: dict[str, list[str]] = {field: [] for field in _REQUIRED_SECTIONS.values()}
    current_field: str | None = None

    for line_number, raw_line in enumerate(policy_text.splitlines(), start=1):
        line = raw_line.strip()

        if line.startswith("## "):
            heading = line[3:].strip()
            current_field = _REQUIRED_SECTIONS.get(heading)
            continue

        if not line or current_field is None:
            continue

        if line.startswith("- "):
            sections[current_field].append(_clean_bullet(line[2:]))
            continue

        raise PolicyParseError(
            f"Unexpected content in policy section at line {line_number}: {raw_line}"
        )

    missing = [
        heading
        for heading, field in _REQUIRED_SECTIONS.items()
        if not sections[field]
    ]
    if missing:
        missing_text = ", ".join(missing)
        raise PolicyParseError(f"Policy is missing required section content: {missing_text}")

    return RepositoryPolicy(
        allowed_paths=tuple(sections["allowed_paths"]),
        prohibited_paths=tuple(sections["prohibited_paths"]),
        approval_required=tuple(sections["approval_required"]),
        validation_expectations=tuple(sections["validation_expectations"]),
    )


def _clean_bullet(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == "`" and text[-1] == "`":
        return text[1:-1]
    return text
