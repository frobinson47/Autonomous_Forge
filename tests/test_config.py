"""Tests for repository-level config defaults (.forge/config.toml)."""

from __future__ import annotations

import argparse
from pathlib import Path

from autonomous_forge.config import ForgeConfig, apply_config_defaults, load_config


class TestLoadConfig:
    def test_missing_file_returns_empty_config(self, tmp_path: Path):
        config = load_config(tmp_path)
        assert config == ForgeConfig()

    def test_parses_defaults_section(self, tmp_path: Path):
        (tmp_path / ".forge").mkdir()
        (tmp_path / ".forge" / "config.toml").write_text(
            '[defaults]\n'
            'plan = ".ai/CUSTOM_PLAN.md"\n'
            'policy = ".forge/custom-policy.md"\n'
            'cmd = "make test"\n',
            encoding="utf-8",
        )
        config = load_config(tmp_path)
        assert config.plan == ".ai/CUSTOM_PLAN.md"
        assert config.policy == ".forge/custom-policy.md"
        assert config.cmd == "make test"

    def test_ignores_keys_outside_defaults_section(self, tmp_path: Path):
        (tmp_path / ".forge").mkdir()
        (tmp_path / ".forge" / "config.toml").write_text(
            '[other]\n'
            'plan = ".ai/SHOULD_NOT_APPLY.md"\n',
            encoding="utf-8",
        )
        config = load_config(tmp_path)
        assert config.plan is None

    def test_ignores_unknown_keys_and_comments(self, tmp_path: Path):
        (tmp_path / ".forge").mkdir()
        (tmp_path / ".forge" / "config.toml").write_text(
            '# a comment\n'
            '[defaults]\n'
            '# another comment\n'
            'unknown_key = "ignored"\n'
            'plan = ".ai/CUSTOM_PLAN.md"\n',
            encoding="utf-8",
        )
        config = load_config(tmp_path)
        assert config.plan == ".ai/CUSTOM_PLAN.md"
        assert config.policy is None

    def test_handles_single_and_unquoted_values(self, tmp_path: Path):
        (tmp_path / ".forge").mkdir()
        (tmp_path / ".forge" / "config.toml").write_text(
            "[defaults]\n"
            "plan = '.ai/SINGLE_QUOTED.md'\n"
            "policy = .forge/unquoted.md\n",
            encoding="utf-8",
        )
        config = load_config(tmp_path)
        assert config.plan == ".ai/SINGLE_QUOTED.md"
        assert config.policy == ".forge/unquoted.md"

    def test_malformed_file_falls_back_to_empty_config(self, tmp_path: Path):
        (tmp_path / ".forge").mkdir()
        (tmp_path / ".forge" / "config.toml").write_text(
            "this is not toml at all {{{\n", encoding="utf-8"
        )
        config = load_config(tmp_path)
        assert config == ForgeConfig()


class TestApplyConfigDefaults:
    def test_fills_omitted_plan_and_policy(self):
        args = argparse.Namespace(plan=None, policy=None)
        config = ForgeConfig(plan=".ai/CUSTOM_PLAN.md", policy=".forge/custom-policy.md")
        apply_config_defaults(args, config)
        assert args.plan == ".ai/CUSTOM_PLAN.md"
        assert args.policy == ".forge/custom-policy.md"

    def test_explicit_flag_wins_over_config(self):
        args = argparse.Namespace(plan="explicit-plan.md", policy=None)
        config = ForgeConfig(plan=".ai/CUSTOM_PLAN.md", policy=".forge/custom-policy.md")
        apply_config_defaults(args, config)
        assert args.plan == "explicit-plan.md"
        assert args.policy == ".forge/custom-policy.md"

    def test_missing_attribute_is_skipped_not_created(self):
        args = argparse.Namespace(root=".")
        config = ForgeConfig(plan=".ai/CUSTOM_PLAN.md")
        apply_config_defaults(args, config)
        assert not hasattr(args, "plan")

    def test_fills_any_cmd_suffixed_attribute(self):
        args = argparse.Namespace(run_cmd=None, commit_cmd="explicit", other=None)
        config = ForgeConfig(cmd="make test")
        apply_config_defaults(args, config)
        assert args.run_cmd == "make test"
        assert args.commit_cmd == "explicit"
        assert args.other is None

    def test_empty_config_changes_nothing(self):
        args = argparse.Namespace(plan=None, policy=None, run_cmd=None)
        apply_config_defaults(args, ForgeConfig())
        assert args.plan is None
        assert args.policy is None
        assert args.run_cmd is None
