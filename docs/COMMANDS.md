# Command Output Contracts

Autonomous Forge commands inspect local files and print human-readable summaries. Most are read-only. Commands that write files or run external processes are noted explicitly.

These contracts describe implemented behavior only. They are intentionally plain so contributors and future automation can rely on stable command purposes without assuming enforcement or execution features that do not exist yet.

## General expectations

- Commands write results to standard output.
- Commands return exit code `0` when the requested read-only inspection succeeds.
- Commands return exit code `2` for missing required input files or malformed roadmap/policy input.
- Most commands should not create, edit, delete, commit, push, run external commands, call networks, read environment variables, scan secrets, or enforce policy decisions. Exceptions are noted per command.
- Output is human-readable and may be extended conservatively, but existing status phrases should remain stable when practical.

## `forge`

Purpose: show the command help when no subcommand is provided.

Inputs: none.

Expected successful output: argparse help that includes available options and subcommands.

Exit codes:

- `0` when help is printed.

Safety limits: help output only; no repository files are read or changed.

## `forge --version`

Purpose: print the installed package version.

Inputs: installed package metadata from `autonomous_forge.__version__`.

Expected successful output pattern:

```text
forge <version>
```

Exit codes:

- `0` when the version is printed.

Safety limits: version output only; no repository files are read or changed.

## `forge tasks`

Purpose: parse roadmap task headings from `.ai/AUTONOMOUS_PLAN.md` or a supplied `--plan` path.

Inputs:

- `--plan`: roadmap Markdown path, defaulting to `.ai/AUTONOMOUS_PLAN.md`.

Expected successful output:

- One line per parsed task in this format:

```text
AUTO-### [P#/STATUS] Task title
```

- If no autonomous tasks are found:

```text
No autonomous tasks found.
```

Exit codes:

- `0` when parsing succeeds.
- `2` when the plan file is missing or a required parsed field is malformed.

Safety limits: reads the plan only; does not select work unless `--next` is provided and does not change files.

## `forge tasks --next`

Purpose: select the next eligible roadmap task without changing files.

Inputs:

- Same `--plan` input as `forge tasks`.

Expected successful output:

```text
AUTO-### [P#/TODO] Task title
```

If no eligible TODO task exists:

```text
No eligible TODO task found.
```

Exit codes:

- `0` when parsing and selection succeed, including the no-task case.
- `2` when the plan file is missing, malformed, or contains an unsupported priority for selection.

Safety limits: reports selection only; does not implement, commit, push, or reserve the task.

## `forge lint-plan`

Purpose: check roadmap task block structure using the documented format.

Inputs:

- `--plan`: roadmap Markdown path, defaulting to `.ai/AUTONOMOUS_PLAN.md`.

Expected successful output:

```text
Plan lint: ok
```

Expected failure output starts with:

```text
Plan lint: failed
```

Diagnostics then use this pattern:

```text
line <number>: <message>
```

Exit codes:

- `0` when no diagnostics are found.
- `2` when the plan file is missing or diagnostics are found.

Safety limits: linting is read-only and does not auto-repair roadmap content.

## `forge report`

Purpose: print a dry-run repository summary.

Inputs:

- `--plan`: roadmap Markdown path, defaulting to `.ai/AUTONOMOUS_PLAN.md`.
- `--state`: state Markdown path, defaulting to `.ai/AUTONOMOUS_STATE.md`.
- `--policy`: policy Markdown path, defaulting to `.forge/policy.md`.

Expected successful output includes these stable lines:

```text
Autonomous Forge dry-run report
Mode: read-only
Plan tasks: <count>
TODO tasks: <count>
DONE tasks: <count>
BLOCKED tasks: <count>
SKIPPED tasks: <count>
Next eligible task: <task-or-none>
State file: present|missing
Policy file: present and readable|missing|malformed: <reason>
Suggested validation: PYTHONPATH=src python -m pytest
```

Exit codes:

- `0` when the report is built.
- `2` when the plan file is missing or malformed.

Safety limits: reports policy readiness only; it does not enforce policy decisions, run validation, or change files.

## `forge policy`

Purpose: parse the repository policy sections and print a conservative readiness summary.

Inputs:

- `--policy`: policy Markdown path, defaulting to `.forge/policy.md`.

Expected successful output:

```text
Repository policy summary
Mode: read-only
Allowed paths: <count>
Prohibited paths: <count>
Human approval required: <count>
Validation expectations: <count>
```

Exit codes:

- `0` when policy parsing succeeds.
- `2` when the policy file is missing or malformed.

Safety limits: parses and counts policy sections only; it does not enforce path decisions or approve changes.

## `forge run-summary`

Purpose: preview the documented local run-summary format without writing an execution-history file.

Inputs:

- `--plan`: roadmap Markdown path, defaulting to `.ai/AUTONOMOUS_PLAN.md`.
- `--policy`: policy Markdown path, defaulting to `.forge/policy.md`.
- `--timestamp`: optional ISO-8601 timestamp for deterministic preview output.

Expected successful output:

```text
Run timestamp: <ISO-8601 timestamp with timezone>
Selected task: <AUTO-### — title, or none>
Task status before run: <TODO|DONE|BLOCKED|SKIPPED|unknown>
Policy status: <present and readable|missing|malformed: reason>
Validation plan: PYTHONPATH=src python -m pytest
Validation result: not run
Changed files summary: none
Commit: none
Notes: Read-only preview only; no run-summary file was written.
```

Exit codes:

- `0` when the preview is built.
- `2` when the plan file is missing, malformed, or contains an unsupported priority for selection.

Safety limits: prints a preview only; it does not create history files, run validation, inspect diffs, commit, push, or change repository files.

## `forge inventory`

Purpose: print repository health inventory file-presence signals for the documented local scope.

Inputs:

- `--root`: repository root to inspect, defaulting to `.`.

Expected successful output:

```text
Repository health inventory
Mode: read-only
Scope: file-presence signals only
.ai/AUTONOMOUS_PLAN.md: present|missing
.ai/AUTONOMOUS_STATE.md: present|missing
.ai/AUTONOMOUS_CHANGELOG.md: present|missing
.ai/DECISIONS.md: present|missing
.forge/policy.md: present|missing
README.md: present|missing
CONTRIBUTING.md: present|missing
LICENSE: present|missing
pyproject.toml: present|missing
src/: present|missing
tests/: present|missing
docs/: present|missing
Health score: not calculated
Notes: Inventory does not enforce policy, scan secrets, read environment variables, call networks, or run external commands.
```

Exit codes:

- `0` when the inventory is built, including repositories with missing expected paths.

Safety limits: reports file-presence signals only; it does not read file contents, calculate a score, scan secrets, read environment variables, call networks, run external commands, enforce policy decisions, or change repository files.

## `forge drift`

Purpose: detect consistency drift between the project's metadata files (plan, state, changelog, policy) and the repository.

Inputs:

- `--plan`: roadmap Markdown path, defaulting to `.ai/AUTONOMOUS_PLAN.md`.
- `--state`: state Markdown path, defaulting to `.ai/AUTONOMOUS_STATE.md`.
- `--changelog`: changelog Markdown path, defaulting to `.ai/AUTONOMOUS_CHANGELOG.md`.
- `--policy`: policy Markdown path, defaulting to `.forge/policy.md`.
- `--root`: repository root for policy path existence checks, defaulting to `.`.

Expected successful output:

```text
Drift report
Mode: read-only
Result: no drift detected|<N> signal(s) detected
[severity] (category) message
...
Notes: Drift detection does not enforce corrections, change files, or run external commands.
```

Signal categories: `state-plan`, `stale-state`, `changelog-plan`, `policy-repo`. Severity levels: `error`, `warn`, `info`.

Exit codes:

- `0` when the drift report is built, including when signals are detected.
- `2` when the plan file is missing or malformed.

Safety limits: reports drift signals only; it does not correct metadata, change files, run external commands, or enforce policy decisions. Missing optional files (state, changelog, policy) are handled gracefully — their checks are skipped.

## `forge pause`

Purpose: capture coding session context (git state and mental model) for handoff across interruptions.

Inputs:

- `--root`: repository root for git state capture and session file storage, defaulting to `.`.
- `--working-on`: what you were working on.
- `--tried`: what you tried so far.
- `--stuck-on`: where you got stuck.
- `--half-finished`: what is half-finished.
- `--next-steps`: what to do next when resuming.
- `--notes`: any additional notes.
- `--timestamp`: optional ISO-8601 timestamp for deterministic output.

Expected successful output:

```text
Session saved: .forge/sessions/session-<timestamp>.md
```

Exit codes:

- `0` when the session is saved.

Safety limits: **this command writes files** to `.forge/sessions/` and **runs `git` as a subprocess** to capture branch, status, log, and stash state. It does not commit, push, modify tracked files, or call networks. Session files are local working state and should be gitignored.

## `forge resume`

Purpose: replay the most recent session context as a structured briefing.

Inputs:

- `--root`: repository root to find session files, defaulting to `.`.

Expected successful output:

```text
Session resume briefing
Last paused: <ISO-8601 timestamp>
Branch: <branch>
Dirty files: <count>
  <file>
  ...
Working on: <text>
Next steps: <text>
...
Recent commits:
  <hash> <message>
  ...
```

If no session files exist:

```text
No session found.
```

Exit codes:

- `0` when the briefing is printed or when no session exists.

Safety limits: reads session files and prints a briefing only; it does not change files, run external commands, or call networks.

## `forge run`

Purpose: execute one autonomous improvement cycle — select a task, validate, diff-check, detect drift, and record the outcome.

Inputs:

- `--root`: repository root, defaulting to `.`.
- `--plan`: roadmap Markdown path (defaults to `.ai/AUTONOMOUS_PLAN.md`).
- `--policy`: policy Markdown path (defaults to `.forge/policy.md`).
- `--cmd`: validation command override.
- `--dry-run`: skip validation execution but still check policy and drift.
- `--no-validate`: skip validation entirely.
- `--no-save`: do not persist the run outcome to `.forge/runs/`.
- `--timestamp`: optional ISO-8601 timestamp for deterministic output.

Expected successful output:

```text
Forge run report
Timestamp: <ISO-8601 timestamp>
Selected task: <AUTO-### — title, or none>
Policy: <present and readable|not found|malformed: reason>
Drift signals: <count>
Changed files: <count>
Diff violations: <count>
Validation: <PASSED|FAILED|skipped (dry run)>
Command: <validation command>
Status: <ready to commit|validation failed — do not commit|idle — no TODO tasks remaining|run complete>
BLOCKED: <reason, if blocked>

Run saved: .forge/runs/run-<timestamp>.md
```

Exit codes:

- `0` when the run completes without being blocked.
- `1` when the run is blocked (prohibited files, error-level drift).
- `2` when required input files are missing.

Safety limits: **this command runs external commands** (validation suite via subprocess) and **writes files** to `.forge/runs/`. It runs `git` to detect changed files. It does NOT auto-commit, push, or modify tracked repository files. Blocked runs halt before validation. Run outcome files are local working state and should be gitignored.

## `forge sync`

Purpose: sync AUTO-xxx tasks from the plan file to Forgejo issues. One-way: plan is the source of truth, Forgejo is the mirror.

Inputs:

- `--root`: repository root, defaulting to `.`.
- `--plan`: roadmap Markdown path (defaults to `.ai/AUTONOMOUS_PLAN.md`).
- `--repo`: Forgejo `owner/repo` (auto-detected from git remote if omitted).
- `--dry-run`: show what would be synced without making API calls.

Expected successful output:

```text
Forge sync report
Repo: <owner/repo>
Tasks synced: <count>
  Created: <count>
  Updated: <count>
  Up to date: <count>

  AUTO-001: created (#1) — Task title
  AUTO-002: up-to-date (#2) — Task title
  ...
```

Exit codes:

- `0` when the sync completes without errors.
- `1` when API errors occur.
- `2` when required input files are missing.

Safety limits: **this command makes network API calls** to the Forgejo instance at `forgejo.familytechlab.com`. It creates and updates issues, labels, and milestones. It does NOT modify local files, commit, push, or change the plan file. Requires `FORGEJO_TOKEN` in environment or `~/.claude/.secrets.env`. The plan file remains the source of truth — Forgejo is the read-only mirror. Re-running is idempotent.

## `forge commit`

Purpose: safe auto-commit with policy and validation pre-flight checks baked in.

Inputs:

- `--root`: repository root, defaulting to `.`.
- `--plan`: roadmap Markdown path (defaults to `.ai/AUTONOMOUS_PLAN.md`).
- `--policy`: policy Markdown path (defaults to `.forge/policy.md`).
- `-m` / `--message`: commit message (auto-generated from current task if omitted).
- `--cmd`: validation command override.
- `--no-validate`: skip validation.
- `--check-only`: run pre-flight checks only, do not commit.

Expected successful output:

```text
Forge commit pre-flight
Task: <AUTO-### — title, if available>
Changed files: <count>
  <file list>
Validation: <PASSED|FAILED>
Result: <SAFE to commit|BLOCKED — reason>

Committed: <short hash>
Message: <commit message>
```

Exit codes:

- `0` when the commit succeeds (or `--check-only` reports SAFE).
- `1` when blocked by prohibited files, validation failure, no changes, or git error.

Safety limits: **this command runs git commit** and **runs external validation commands** via subprocess. It checks staged files against policy before committing. It does NOT push, modify the plan file, or auto-stage files. Auto-generated commit messages use the format `forge: AUTO-### — title`.
