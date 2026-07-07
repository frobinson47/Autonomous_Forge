from autonomous_forge.cli import main
from autonomous_forge.init import init_forge, format_init_result


def test_init_creates_all_metadata_files(tmp_path):
    result = init_forge(tmp_path, project_name="test-project", date="2026-07-07")

    assert ".ai/AUTONOMOUS_PLAN.md" in result.created
    assert ".ai/AUTONOMOUS_STATE.md" in result.created
    assert ".ai/AUTONOMOUS_CHANGELOG.md" in result.created
    assert ".ai/DECISIONS.md" in result.created
    assert ".forge/policy.md" in result.created
    assert ".gitignore" in result.created

    plan = (tmp_path / ".ai" / "AUTONOMOUS_PLAN.md").read_text(encoding="utf-8")
    assert "test-project" in plan
    assert "Roadmap v1" in plan

    policy = (tmp_path / ".ai" / "AUTONOMOUS_STATE.md").read_text(encoding="utf-8")
    assert "Current roadmap version: v1" in policy

    changelog = (tmp_path / ".ai" / "AUTONOMOUS_CHANGELOG.md").read_text(encoding="utf-8")
    assert "2026-07-07" in changelog
    assert "test-project" in changelog


def test_init_skips_existing_files(tmp_path):
    (tmp_path / ".ai").mkdir()
    (tmp_path / ".ai" / "AUTONOMOUS_PLAN.md").write_text("# Existing\n", encoding="utf-8")

    result = init_forge(tmp_path, project_name="test-project", date="2026-07-07")

    assert ".ai/AUTONOMOUS_PLAN.md" in result.skipped
    assert ".ai/AUTONOMOUS_STATE.md" in result.created
    existing = (tmp_path / ".ai" / "AUTONOMOUS_PLAN.md").read_text(encoding="utf-8")
    assert existing == "# Existing\n"


def test_init_appends_to_existing_gitignore(tmp_path):
    (tmp_path / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")

    result = init_forge(tmp_path, project_name="test", date="2026-07-07")

    assert ".gitignore (appended)" in result.created
    content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert "__pycache__/" in content
    assert ".forge/sessions/" in content


def test_init_skips_gitignore_if_already_has_sessions(tmp_path):
    (tmp_path / ".gitignore").write_text(".forge/sessions/\n", encoding="utf-8")

    result = init_forge(tmp_path, project_name="test", date="2026-07-07")

    assert any("already has" in s for s in result.skipped)


def test_format_init_result_shows_created_and_skipped():
    from autonomous_forge.init import InitResult

    result = InitResult(
        created=(".ai/AUTONOMOUS_PLAN.md",),
        skipped=(".forge/policy.md",),
    )
    output = format_init_result(result)
    assert "Created 1 file(s)" in output
    assert "Skipped 1 file(s)" in output


def test_init_cli_command(tmp_path, capsys):
    result = main(["init", "--root", str(tmp_path), "--name", "cli-test"])
    assert result == 0
    output = capsys.readouterr().out
    assert "Forge initialized" in output
    assert (tmp_path / ".ai" / "AUTONOMOUS_PLAN.md").exists()
