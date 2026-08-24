"""Tests for the advisory task-scope check (AUTO-062 / DEC-016)."""

from __future__ import annotations

from autonomous_forge.scope import find_out_of_scope_files


def test_empty_expected_files_flags_nothing():
    assert find_out_of_scope_files(["src/foo.py"], "") == ()


def test_prose_only_expected_files_flags_nothing():
    # No usable path-shaped tokens — absence of a declaration isn't
    # evidence of a mismatch.
    assert find_out_of_scope_files(["src/foo.py"], "   ") == ()


def test_matching_file_not_flagged():
    assert find_out_of_scope_files(["src/foo.py"], "src/") == ()


def test_non_matching_file_flagged():
    assert find_out_of_scope_files(["docs/readme.md"], "src/") == ("docs/readme.md",)


def test_comma_separated_tokens():
    result = find_out_of_scope_files(
        ["src/foo.py", "tests/test_foo.py", "docs/readme.md"],
        "src/, tests/",
    )
    assert result == ("docs/readme.md",)


def test_exact_file_token():
    assert find_out_of_scope_files(["pyproject.toml"], "pyproject.toml") == ()


def test_glob_token():
    assert find_out_of_scope_files(["src/autonomous_forge/check.py"], "src/**") == ()
    assert find_out_of_scope_files(["docs/readme.md"], "src/**") == ("docs/readme.md",)


def test_backtick_wrapped_token():
    assert find_out_of_scope_files(["src/foo.py"], "`src/`") == ()


def test_bare_word_matches_filename_without_extension():
    # "README" (no extension, no slash) is common prose for README.md.
    assert find_out_of_scope_files(["README.md"], "README.") == ()


def test_bare_word_matches_directory_without_trailing_slash():
    assert find_out_of_scope_files(["docs/COMMANDS.md"], "docs") == ()


def test_real_project_style_sentence_field():
    # Matches this project's actual plan-file style: backtick-quoted,
    # comma-separated, trailing full stop on the last token.
    text = "`src/autonomous_forge/plan.py`, `src/autonomous_forge/cli.py`, tests, README."
    changed = [
        "src/autonomous_forge/plan.py",
        "tests/test_plan.py",
        "README.md",
        "docs/COMMANDS.md",
    ]
    assert find_out_of_scope_files(changed, text) == ("docs/COMMANDS.md",)
