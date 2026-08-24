"""Advisory check: do staged changes match the selected task's declared scope?

`Expected files or areas` is free-form prose written by whoever authored the
task, not a strict policy — this module never blocks a commit, only reports
files that don't obviously match. See DEC-016 for why this is advisory-only.
"""

from __future__ import annotations

import fnmatch
import re

_TOKEN_SPLIT_RE = re.compile(r"[,\n]")


def _normalize_token(token: str) -> str:
    # Real "Expected files or areas" fields are written as backtick-quoted,
    # comma-separated sentences ("...`cli.py`, tests, README.") — the last
    # token before the full stop otherwise keeps a trailing "`."/"." that
    # never matches a real path.
    token = token.strip()
    token = re.sub(r"^`+", "", token)
    token = re.sub(r"[`.]+$", "", token)
    return token.rstrip("/")


def _token_matches(filepath: str, token: str) -> bool:
    normalized = _normalize_token(token)
    if not normalized:
        return False
    filepath = filepath.replace("\\", "/")
    if "*" in normalized:
        if fnmatch.fnmatch(filepath, normalized):
            return True
        parts = filepath.split("/")
        return any(
            fnmatch.fnmatch("/".join(parts[i:]), normalized)
            for i in range(len(parts))
        )
    if "/" not in normalized:
        # A bare word ("README", "docs", "tests") is ambiguous prose —
        # could mean a specific file referenced without its extension, or
        # a whole directory referenced without a trailing slash. Try both.
        basename = filepath.rsplit("/", 1)[-1]
        stem = basename.split(".", 1)[0]
        if normalized in (basename, stem) or basename.startswith(normalized + "."):
            return True
    return filepath == normalized or filepath.startswith(normalized + "/")


def find_out_of_scope_files(
    changed_files: list[str],
    expected_files_text: str,
) -> tuple[str, ...]:
    """Return changed files not covered by any token in expected_files_text.

    Tokens are comma/newline-separated fragments from the task's
    `Expected files or areas` field, matched as either a glob (if the
    token contains `*`) or a path/prefix match otherwise. An empty or
    unparseable field returns no results — the absence of a usable
    declaration is not evidence of a mismatch.
    """
    tokens = [
        t for t in (tok.strip() for tok in _TOKEN_SPLIT_RE.split(expected_files_text)) if t
    ]
    if not tokens:
        return ()
    return tuple(
        f for f in changed_files if not any(_token_matches(f, t) for t in tokens)
    )
