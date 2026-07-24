# Autonomous Forge

Autonomous Forge is an open-source, AI-built and AI-maintained developer tool for safely running repository-native autonomous software-improvement loops.

It keeps a durable, human-readable roadmap (`.ai/AUTONOMOUS_PLAN.md`) as the single source of truth for what work is next, then provides a `forge` CLI that can select a task, validate it, check it against a repository policy, commit, push, and sync the result to a Forgejo issue tracker — with every stage gated behind explicit opt-in flags and a conservative, documented policy boundary for anything higher-risk.

## What it gives you

- **A durable plan-of-record.** Tasks live in a roadmap file with IDs, priorities, and statuses. `forge tasks --next` deterministically picks the next eligible task — no manual triage.
- **A full opt-in pipeline.** `forge run` → `forge commit` → `forge push` → `forge sync` (or all four at once via `forge pipeline --commit --push --sync`) — validate, diff-check, commit, push, and mirror status to Forgejo, one flag per stage.
- **A repository policy layer.** `.forge/policy.md` defines allowed paths, prohibited paths, and categories requiring explicit human approval. `forge commit`/`forge check` enforce it before anything is committed.
- **Drift and lint detection.** `forge drift` and `forge lint-plan` catch inconsistency between the plan, state, changelog, and policy files before it compounds.
- **Session continuity.** `forge pause` / `forge resume` capture full git state and working context so a session (human or agent) can pick back up with zero ramp-up — including a combined `--roots` briefing across multiple repos.
- **Run history and metrics.** Every `forge run` is recorded to `.forge/runs/`; `forge log` and `forge metrics` surface pass rate, drift signals, and violations over time.
- **A read-only watch loop.** `forge watch` re-runs lint + drift + diff-check + validation on a timer, catching regressions between sessions without a cron/daemon setup.
- **One-way Forgejo issue sync.** `forge sync` mirrors plan tasks to issues/labels/milestones (plan is always the source of truth); `forge sync --report-orphans` flags issues with no matching plan task, read-only.

## Current status

Autonomous Forge is pre-1.0 but functional end-to-end: Roadmap v1–v4 are complete (37/37 tasks), with the full pipeline, policy enforcement, drift detection, session handoff, run metrics, and Forgejo sync all implemented and tested (253 tests passing). See `.ai/AUTONOMOUS_PLAN.md` and `.ai/AUTONOMOUS_STATE.md` for the current roadmap and state.

## Install for local development

```bash
python -m pip install -e .
forge --help
```

For full setup, contribution workflow, and safety expectations, see `CONTRIBUTING.md`.

## Quickstart

```bash
# See what's next on the roadmap
forge status

# Preview what a run would do, without changing anything
forge run --dry-run

# Run the next eligible task, then commit, push, and sync it
forge pipeline --commit --push --sync

# Check plan/state/policy consistency and run validation
forge check

# Capture session context before stepping away
forge pause --working-on "..." --next-steps "..."

# Pick back up later, or across multiple repos
forge resume
forge resume --roots ../repo-a,../repo-b
```

## Command reference

Every command's inputs, output format, exit codes, and safety limits are documented in `docs/COMMANDS.md`. Highlights:

| Command | Purpose |
|---|---|
| `forge tasks [--next]` | List or select roadmap tasks (read-only) |
| `forge lint-plan` | Validate roadmap structure (read-only) |
| `forge drift` | Detect plan/state/changelog/policy inconsistency (read-only) |
| `forge report` | Dry-run repository summary (read-only) |
| `forge run` | Select, validate, diff-check, and record one task cycle |
| `forge commit` | Policy-checked, validated auto-commit |
| `forge push` | Push committed work to the git remote |
| `forge sync [--report-orphans]` | One-way plan → Forgejo issue sync, or read-only orphan report |
| `forge pipeline` | Run → commit → push → sync, each stage opt-in |
| `forge mark` / `forge plan add` | Update task status / append a new task |
| `forge check` / `forge watch` | Run (or periodically re-run) lint + drift + diff-check + validation |
| `forge doctor` | Diagnose environment issues (token, git remote, reachability) before a run |
| `forge log` / `forge metrics` | Run history and aggregate stats |
| `forge pause` / `forge resume` | Session handoff, single-repo or cross-repo |
| `forge policy` / `forge inventory` | Policy readiness / repository health signals (read-only) |

Repo-level defaults for `--plan`/`--policy`/`--cmd` can be set once in `.forge/config.toml` (scaffolded by `forge init`) instead of passed on every invocation — see `docs/COMMANDS.md`.

See also:

- `docs/COMMANDS.md` — full command output contracts.
- `docs/RUN_SUMMARIES.md` — the local run-summary format written by `forge run`.
- `docs/HEALTH_INVENTORY.md` — the `forge inventory` scope and safety boundaries.

## Repository policy boundaries

Policy documentation lives in `docs/POLICY.md`. The current example policy lives in `.forge/policy.md` and defines:

- paths that routine autonomous work may consider;
- prohibited paths that should not be changed automatically;
- categories that require explicit human approval;
- validation expectations before a change is committed.

The policy format is conservative by design. If future tooling cannot read or understand a policy file, it should avoid implementation work rather than guessing. `forge commit`, `forge check`, and `forge pipeline` all enforce this policy before committing.

## Run tests

```bash
PYTHONPATH=src python -m pytest
```

## Safe contribution expectations

Contributions should stay small, local-first, and reviewable. Higher-risk categories (network actions beyond documented Forgejo sync, external command execution beyond documented validation, secret handling, deployment behavior, telemetry, or repository-permission changes) require explicit roadmap and policy approval — see `CONTRIBUTING.md` and `.forge/policy.md`.
