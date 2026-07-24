"""Repository-level command defaults read from .forge/config.toml.

Config values only fill in flags the user omitted — an explicit CLI flag
always wins, and a missing or malformed config file falls back to each
command's existing hardcoded default with no behavior change.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


CONFIG_RELATIVE_PATH = Path(".forge") / "config.toml"

DEFAULT_CONFIG_TEMPLATE = """\
# Autonomous Forge repository defaults.
# Any value here fills in a command flag only when it was omitted on the
# command line — explicit flags always win. Delete or leave a key unset to
# fall back to that command's built-in default.
[defaults]
# plan = ".ai/AUTONOMOUS_PLAN.md"
# policy = ".forge/policy.md"
# cmd = "PYTHONPATH=src python -m pytest"
"""


@dataclass(frozen=True)
class ForgeConfig:
    """Parsed repo-level defaults. Any field may be unset (None)."""

    plan: str | None = None
    policy: str | None = None
    cmd: str | None = None


def load_config(root: Path = Path(".")) -> ForgeConfig:
    """Read .forge/config.toml under ``root`` if present.

    Supports only a flat ``[defaults]`` section of ``key = "value"`` pairs
    for ``plan``, ``policy``, and ``cmd`` — a minimal, dependency-free
    subset of TOML, not a general parser (this project targets Python
    3.10+, and stdlib ``tomllib`` requires 3.11+). Any other key, section,
    or malformed line is ignored rather than raised, so a missing or
    partially-written config file degrades to "no defaults" instead of
    breaking every command.
    """
    path = root / CONFIG_RELATIVE_PATH
    if not path.exists():
        return ForgeConfig()

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ForgeConfig()

    values: dict[str, str] = {}
    in_defaults = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            in_defaults = line[1:-1].strip() == "defaults"
            continue
        if not in_defaults or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key in ("plan", "policy", "cmd") and value:
            values[key] = value

    return ForgeConfig(
        plan=values.get("plan"),
        policy=values.get("policy"),
        cmd=values.get("cmd"),
    )


def apply_config_defaults(args: argparse.Namespace, config: ForgeConfig) -> None:
    """Fill in omitted --plan/--policy/--cmd-family flags from config, in place.

    Only touches attributes that already exist on ``args`` and are still
    ``None`` after argument parsing — an explicit CLI flag is never
    overwritten. Safe to call for any subcommand's namespace; subcommands
    that don't define a given flag simply have no matching attribute.
    """
    if config.plan and getattr(args, "plan", None) is None and hasattr(args, "plan"):
        args.plan = config.plan
    if config.policy and getattr(args, "policy", None) is None and hasattr(args, "policy"):
        args.policy = config.policy
    if config.cmd:
        for attr in list(vars(args)):
            if attr.endswith("_cmd") and getattr(args, attr) is None:
                setattr(args, attr, config.cmd)
