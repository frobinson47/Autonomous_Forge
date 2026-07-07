from autonomous_forge.cli import main
from autonomous_forge.context import build_project_context


PLAN_WITH_TODO = """\
### AUTO-001 — First task
Priority: P1
Status: DONE
Goal: Do the first thing.
Why it matters: Foundation.
Scope: Small.
Expected files or areas: src/.
Acceptance criteria: It works.
Validation: Tests pass.
Risks or assumptions: None.
Notes: None.

### AUTO-002 — Second task
Priority: P2
Status: TODO
Goal: Do the second thing.
Why it matters: Progress.
Scope: Small.
Expected files or areas: src/.
Acceptance criteria: It works.
Validation: Tests pass.
Risks or assumptions: None.
Notes: None.
"""

STATE_CLEAN = """\
# Autonomous State

- Current task ID: AUTO-002 — Second task
- Current task status: TODO
- Current branch: main
- Last successful commit hash: abc123
- Current blockers: None
"""

POLICY_VALID = """\
# Policy

## Allowed paths

- src/**

## Prohibited paths

- .env

## Human approval required

- Adding network access.

## Validation expectations

- Run tests.
"""


def test_full_context_with_all_metadata(tmp_path):
    ai_dir = tmp_path / ".ai"
    ai_dir.mkdir()
    (ai_dir / "AUTONOMOUS_PLAN.md").write_text(PLAN_WITH_TODO, encoding="utf-8")
    (ai_dir / "AUTONOMOUS_STATE.md").write_text(STATE_CLEAN, encoding="utf-8")
    (ai_dir / "AUTONOMOUS_CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    forge_dir = tmp_path / ".forge"
    forge_dir.mkdir()
    (forge_dir / "policy.md").write_text(POLICY_VALID, encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "README.md").write_text("# Hi\n", encoding="utf-8")

    output = build_project_context(tmp_path)

    assert "Project context:" in output
    assert "Mode: read-only" in output
    assert "2 total" in output
    assert "1 done" in output
    assert "1 todo" in output
    assert "Next task: AUTO-002" in output
    assert "Current task: AUTO-002" in output
    assert "1 allowed" in output
    assert "Drift: none detected" in output


def test_context_without_plan(tmp_path):
    output = build_project_context(tmp_path)
    assert "not found" in output.lower() or "not use Autonomous Forge" in output


def test_context_with_drift(tmp_path):
    ai_dir = tmp_path / ".ai"
    ai_dir.mkdir()
    (ai_dir / "AUTONOMOUS_PLAN.md").write_text(PLAN_WITH_TODO, encoding="utf-8")
    (ai_dir / "AUTONOMOUS_STATE.md").write_text(
        "# State\n- Current task ID: AUTO-002\n- Current task status: DONE\n"
        "- Last successful commit hash: pending\n",
        encoding="utf-8",
    )

    output = build_project_context(tmp_path)

    assert "signal(s)" in output


def test_context_shows_missing_health_files(tmp_path):
    ai_dir = tmp_path / ".ai"
    ai_dir.mkdir()
    (ai_dir / "AUTONOMOUS_PLAN.md").write_text(PLAN_WITH_TODO, encoding="utf-8")

    output = build_project_context(tmp_path)

    assert "missing" in output.lower()


def test_context_cli_command(tmp_path, capsys):
    ai_dir = tmp_path / ".ai"
    ai_dir.mkdir()
    (ai_dir / "AUTONOMOUS_PLAN.md").write_text(PLAN_WITH_TODO, encoding="utf-8")

    result = main(["context", "--root", str(tmp_path)])
    assert result == 0

    output = capsys.readouterr().out
    assert "Project context:" in output
    assert "Mode: read-only" in output
