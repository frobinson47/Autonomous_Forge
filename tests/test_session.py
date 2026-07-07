from pathlib import Path

from autonomous_forge.cli import main
from autonomous_forge.session import (
    GitSnapshot,
    SessionContext,
    build_session_snapshot,
    deserialize_session,
    format_resume_briefing,
    load_latest_session,
    save_session,
    serialize_session,
)


def _make_git_snapshot(**overrides):
    defaults = dict(
        branch="main",
        dirty_files=(),
        recent_commits=(),
        stash_list=(),
    )
    defaults.update(overrides)
    return GitSnapshot(**defaults)


def _make_session(**overrides):
    defaults = dict(
        timestamp="2026-07-07T12:00:00+00:00",
        git=_make_git_snapshot(),
        working_on="",
        tried="",
        stuck_on="",
        half_finished="",
        next_steps="",
        notes="",
    )
    defaults.update(overrides)
    return SessionContext(**defaults)


def test_serialize_minimal_session():
    ctx = _make_session()
    text = serialize_session(ctx)
    assert "# Session Handoff" in text
    assert "Paused: 2026-07-07T12:00:00+00:00" in text
    assert "Branch: main" in text


def test_serialize_full_session():
    ctx = _make_session(
        git=_make_git_snapshot(
            branch="feature/auth",
            dirty_files=("src/auth.py", "tests/test_auth.py"),
            recent_commits=("abc123 add login", "def456 fix typo"),
            stash_list=("stash@{0}: WIP on feature/auth",),
        ),
        working_on="Adding OAuth flow",
        tried="Tried direct token exchange but hit CORS",
        stuck_on="CORS preflight on token endpoint",
        half_finished="Token refresh logic in auth.py",
        next_steps="Try proxy approach through backend",
        notes="Check if Authentik supports PKCE",
    )
    text = serialize_session(ctx)
    assert "feature/auth" in text
    assert "src/auth.py" in text
    assert "abc123 add login" in text
    assert "stash@{0}" in text
    assert "Adding OAuth flow" in text
    assert "CORS preflight" in text
    assert "Token refresh" in text
    assert "proxy approach" in text
    assert "PKCE" in text


def test_roundtrip_serialize_deserialize():
    original = _make_session(
        git=_make_git_snapshot(
            branch="fix/bug-42",
            dirty_files=("a.py", "b.py"),
            recent_commits=("111 first", "222 second"),
            stash_list=("stash@{0}: WIP",),
        ),
        working_on="Fixing the widget",
        tried="Tried patching upstream",
        stuck_on="Race condition in worker",
        half_finished="Partial lock implementation",
        next_steps="Add mutex around shared state",
        notes="Might need to refactor worker pool",
    )
    text = serialize_session(original)
    restored = deserialize_session(text)

    assert restored.timestamp == original.timestamp
    assert restored.git.branch == original.git.branch
    assert restored.git.dirty_files == original.git.dirty_files
    assert restored.git.recent_commits == original.git.recent_commits
    assert restored.git.stash_list == original.git.stash_list
    assert restored.working_on == original.working_on
    assert restored.tried == original.tried
    assert restored.stuck_on == original.stuck_on
    assert restored.half_finished == original.half_finished
    assert restored.next_steps == original.next_steps
    assert restored.notes == original.notes


def test_roundtrip_minimal():
    original = _make_session()
    text = serialize_session(original)
    restored = deserialize_session(text)
    assert restored.timestamp == original.timestamp
    assert restored.git.branch == "main"


def test_save_and_load_session(tmp_path):
    ctx = _make_session(working_on="Testing save/load")
    saved_path = save_session(ctx, tmp_path)
    assert saved_path.exists()
    assert saved_path.parent.name == "sessions"

    loaded = load_latest_session(tmp_path)
    assert loaded is not None
    assert loaded.working_on == "Testing save/load"
    assert loaded.timestamp == ctx.timestamp


def test_load_latest_returns_none_when_no_sessions(tmp_path):
    assert load_latest_session(tmp_path) is None


def test_load_latest_picks_most_recent(tmp_path):
    ctx1 = _make_session(timestamp="2026-07-07T10:00:00+00:00", working_on="first")
    ctx2 = _make_session(timestamp="2026-07-07T11:00:00+00:00", working_on="second")
    save_session(ctx1, tmp_path)
    save_session(ctx2, tmp_path)

    loaded = load_latest_session(tmp_path)
    assert loaded is not None
    assert loaded.working_on == "second"


def test_format_resume_briefing():
    ctx = _make_session(
        git=_make_git_snapshot(
            branch="main",
            dirty_files=("file.py",),
            recent_commits=("abc fix bug",),
            stash_list=("stash@{0}: WIP",),
        ),
        working_on="Bug fix",
        next_steps="Write tests",
    )
    briefing = format_resume_briefing(ctx)
    assert "Session resume briefing" in briefing
    assert "Branch: main" in briefing
    assert "Dirty files: 1" in briefing
    assert "file.py" in briefing
    assert "Stashed: 1" in briefing
    assert "Working on: Bug fix" in briefing
    assert "Next steps: Write tests" in briefing
    assert "abc fix bug" in briefing


def test_pause_cli_saves_session(tmp_path, capsys):
    result = main([
        "pause",
        "--root", str(tmp_path),
        "--working-on", "Building the widget",
        "--next-steps", "Add tests",
        "--timestamp", "2026-07-07T15:00:00+00:00",
    ])
    assert result == 0
    output = capsys.readouterr().out
    assert "Session saved:" in output

    sessions = list((tmp_path / ".forge" / "sessions").glob("session-*.md"))
    assert len(sessions) == 1


def test_resume_cli_prints_briefing(tmp_path, capsys):
    ctx = _make_session(working_on="Testing resume CLI", next_steps="Ship it")
    save_session(ctx, tmp_path)

    result = main(["resume", "--root", str(tmp_path)])
    assert result == 0
    output = capsys.readouterr().out
    assert "Session resume briefing" in output
    assert "Testing resume CLI" in output
    assert "Ship it" in output


def test_resume_cli_no_sessions(tmp_path, capsys):
    result = main(["resume", "--root", str(tmp_path)])
    assert result == 0
    output = capsys.readouterr().out
    assert "No session found" in output
