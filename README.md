# Autonomous Forge

Autonomous Forge is an open-source, AI-built and AI-maintained developer tool for safely running repository-native autonomous software-improvement loops.

The project starts as a local-first Python CLI. Its first goal is deliberately small: provide a `forge` command that can grow into dry-run planning, task selection, validation reporting, and durable repository memory without requiring uncontrolled autonomous behavior.

## Current status

Autonomous Forge is pre-alpha. The repository now contains:

- Apache-2.0 licensing.
- Durable autonomous planning files in `.ai/`.
- A minimal Python package scaffold.
- A `forge` console script entry point.
- A smoke test for the CLI help output.

## Planned direction

The MVP roadmap focuses on practical, reviewable automation:

1. Scaffold a local CLI and package metadata.
2. Parse roadmap task headings from `.ai/AUTONOMOUS_PLAN.md`.
3. Select one eligible task deterministically.
4. Produce a read-only dry-run repository report.
5. Document repository policy boundaries before any higher-risk behavior.

## Install for local development

```bash
python -m pip install -e .
forge --help
```

## Run tests

```bash
PYTHONPATH=src python -m pytest
```

## Safe contribution expectations

Contributions should stay small, local-first, and reviewable. Do not add network actions, external command execution, secret handling, deployment behavior, telemetry, or repository-permission changes unless the roadmap and repository policy explicitly allow it.
