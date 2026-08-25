"""Best-effort redaction of credential-shaped text before it is persisted.

This is defense in depth, not secret detection. Known provider key formats
and configured secret-like environment values are redacted; arbitrary
program output can still leak a credential in a shape no pattern here
recognizes. See SECURITY.md.
"""

from __future__ import annotations

import re
from typing import Mapping

_REDACTED = "[REDACTED]"

# Provider key prefixes with a reasonably distinctive shape, so this
# doesn't fire on ordinary words. Order doesn't matter — all are applied.
_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}"),  # Anthropic
    re.compile(r"sk-proj-[A-Za-z0-9_-]{10,}"),  # OpenAI project key
    re.compile(r"sk-svcacct-[A-Za-z0-9_-]{10,}"),  # OpenAI service account key
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI legacy key
    re.compile(r"xai-[A-Za-z0-9_-]{10,}"),  # xAI
    re.compile(r"AIzaSy[A-Za-z0-9_-]{25,}"),  # Google API key
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),  # GitHub personal access token
    re.compile(r"gho_[A-Za-z0-9]{30,}"),  # GitHub OAuth token
    re.compile(r"ghu_[A-Za-z0-9]{30,}"),  # GitHub user-to-server token
    re.compile(r"ghs_[A-Za-z0-9]{30,}"),  # GitHub server-to-server token
    re.compile(r"ghr_[A-Za-z0-9]{30,}"),  # GitHub refresh token
    re.compile(r"AKIA[A-Z0-9]{16}"),  # AWS access key ID
    re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-.=]{10,}"),  # bearer tokens
    # key/token/secret/password = <value>, quoted or not — a common shape
    # in CLI --flag output, env dumps, and config-file echoes.
    re.compile(
        r'(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*'
        r'["\']?([A-Za-z0-9_\-./+=]{8,})["\']?'
    ),
]

# Environment variable names whose values are treated as secrets regardless
# of shape, if their value appears verbatim in the text being redacted.
_SECRET_NAME_RE = re.compile(r"(?i)(key|token|secret|password|credential)")


def _apply_patterns(text: str) -> str:
    for pattern in _PATTERNS:
        if pattern.groups:
            text = pattern.sub(lambda m: m.group(0).replace(m.group(2), _REDACTED), text)
        else:
            text = pattern.sub(_REDACTED, text)
    return text


def redact_secrets(text: str, env: Mapping[str, str] | None = None) -> str:
    """Return text with credential-shaped substrings replaced by [REDACTED].

    Applies known provider key-format patterns, then — if ``env`` is
    given — also redacts the exact value of any environment variable whose
    name looks secret-like (contains "key", "token", "secret", "password",
    or "credential"), so a printed env dump doesn't defeat the shape-based
    patterns above. Values shorter than 8 characters are skipped to avoid
    redacting short, common substrings (flags, single words) by accident.
    """
    if not text:
        return text
    redacted = _apply_patterns(text)
    if env:
        for name, value in env.items():
            if len(value) >= 8 and _SECRET_NAME_RE.search(name) and value in redacted:
                redacted = redacted.replace(value, _REDACTED)
    return redacted
