import pytest

from autonomous_forge.policy import (
    PolicyParseError,
    parse_repository_policy,
)


VALID_POLICY = """# Autonomous Forge Policy

## Allowed paths

- `src/**`
- `tests/**`

## Prohibited paths

- `.env`
- `**/*.pem`

## Human approval required

- Adding network access.

## Validation expectations

- Run targeted tests.
"""


def test_parse_repository_policy_sections():
    policy = parse_repository_policy(VALID_POLICY)

    assert policy.allowed_paths == ("src/**", "tests/**")
    assert policy.prohibited_paths == (".env", "**/*.pem")
    assert policy.approval_required == ("Adding network access.",)
    assert policy.validation_expectations == ("Run targeted tests.",)


def test_parse_repository_policy_rejects_missing_required_section_content():
    with pytest.raises(PolicyParseError, match="Validation expectations"):
        parse_repository_policy(
            """## Allowed paths
- `src/**`

## Prohibited paths
- `.env`

## Human approval required
- Adding network access.

## Validation expectations
"""
        )


def test_parse_repository_policy_rejects_unexpected_section_content():
    with pytest.raises(PolicyParseError, match="Unexpected content"):
        parse_repository_policy(
            """## Allowed paths
src/**

## Prohibited paths
- `.env`

## Human approval required
- Adding network access.

## Validation expectations
- Run tests.
"""
        )
