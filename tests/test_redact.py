"""Tests for best-effort secret redaction (AUTO-066 / SEC-004)."""

from __future__ import annotations

from autonomous_forge.redact import redact_secrets


def test_empty_text_returns_empty():
    assert redact_secrets("") == ""


def test_plain_text_unchanged():
    text = "10 passed in 1.23s"
    assert redact_secrets(text) == text


def test_anthropic_key_redacted():
    # Built via concatenation so this fixture isn't itself a contiguous
    # credential-shaped literal that a secret scanner would flag.
    fake_key = "sk-ant-" + "abc123DEF456ghi789"
    text = f"using key {fake_key}"
    result = redact_secrets(text)
    assert "sk-ant-" not in result
    assert "[REDACTED]" in result


def test_openai_project_key_redacted():
    fake_key = "sk-proj-" + "abcdefghij1234567890"
    text = f"OPENAI_API_KEY={fake_key}"
    result = redact_secrets(text)
    assert "sk-proj-" not in result


def test_github_pat_redacted():
    fake_key = "ghp_" + "abcdefghij1234567890abcdefghij12"
    text = f"token: {fake_key}"
    result = redact_secrets(text)
    assert "ghp_" not in result


def test_aws_access_key_redacted():
    fake_key = "AKIA" + "IOSFODNN7EXAMPLE"
    text = f"AWS_ACCESS_KEY_ID={fake_key}"
    result = redact_secrets(text)
    assert fake_key not in result


def test_bearer_token_redacted():
    text = "Authorization: Bearer abcdef123456xyz"
    result = redact_secrets(text)
    assert "abcdef123456xyz" not in result


def test_generic_secret_assignment_redacted():
    text = 'password: "hunter2longenough"'
    result = redact_secrets(text)
    assert "hunter2longenough" not in result
    assert "password" in result  # field name preserved, only value redacted


def test_short_values_not_redacted():
    text = "password: short"
    result = redact_secrets(text)
    assert result == text


def test_env_secret_name_value_redacted():
    text = "output included FORGEJO_TOKEN_VALUE_XYZ somewhere in the log"
    env = {"FORGEJO_TOKEN": "FORGEJO_TOKEN_VALUE_XYZ"}
    result = redact_secrets(text, env=env)
    assert "FORGEJO_TOKEN_VALUE_XYZ" not in result
    assert "[REDACTED]" in result


def test_env_non_secret_name_not_redacted():
    text = "PATH value appears here: /usr/local/bin"
    env = {"PATH": "/usr/local/bin"}
    result = redact_secrets(text, env=env)
    assert result == text


def test_env_short_value_not_redacted():
    text = "API_KEY is set"
    env = {"API_KEY": "abc"}
    result = redact_secrets(text, env=env)
    assert result == text
