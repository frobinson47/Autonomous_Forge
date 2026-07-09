# Autonomous Forge Roadmap

## Product vision

Autonomous Forge helps a repository keep a clear improvement plan, choose one small task, check the result, and record what happened.

## Product scope and non-goals

The first product remains a local Python command-line tool. It reads repository files, reports safe next actions, and keeps durable project memory. It is not a hosted platform, dashboard, autonomous executor, deployment system, or permission-management tool.

## Current architecture

The project has two interfaces: a Python CLI (`forge`) and Claude Code skills (`/pause`, `/resume`). The Python package lives under `src/autonomous_forge` with tests under `tests/`. The CLI exposes `forge tasks`, `forge tasks --next`, `forge lint-plan`, `forge report`, `forge policy`, `forge run-summary`, `forge inventory`, `forge drift`, `forge pause`, and `forge resume`. The Claude Code skills live in global config (`~/.claude/commands/`) and work in any repo. Session handoff files are stored in `.forge/sessions/` (gitignored). The project uses zero runtime dependencies; `forge pause` shells out to `git` for state capture.

## Current implementation status

Roadmaps v1 and v2 are complete (14 tasks). Roadmap v3 has added metadata drift detection and session handoff. All 54 tests pass at runtime. The session `pause` command is the first feature that writes files (session snapshots) and runs an external command (`git`).

## Technical debt

The CLI does not yet persist run summaries in a machine-readable local format. The `docs/COMMANDS.md` file does not document the `drift`, `pause`, or `resume` commands yet.

## Prioritized roadmap

## Roadmap v1

### AUTO-001 — Scaffold local CLI and package metadata
Priority: P1
Status: DONE

Goal: Create a minimal installable Python CLI with a `forge` command.
Why it matters: A stable command surface is needed before planner behavior can be used.
Scope: Add package metadata, source layout, CLI help, and a smoke test.
Expected files or areas: `pyproject.toml`, `src/`, `tests/`, README.
Acceptance criteria: `forge --help` succeeds and describes the dry-run focus.
Validation: Static review completed; test command documented but not executed in this tool runtime.
Risks or assumptions: Python is selected for low overhead.
Notes: Keep runtime dependencies at zero.

### AUTO-002 — Parse autonomous plan task headings
Priority: P1
Status: DONE

Goal: Read task headings and statuses from `.ai/AUTONOMOUS_PLAN.md`.
Why it matters: Task visibility is required for deterministic selection.
Scope: Read Markdown locally and return task identifiers, titles, priorities, and statuses.
Expected files or areas: `src/autonomous_forge/plan.py`, `src/autonomous_forge/cli.py`, tests, README.
Acceptance criteria: Valid blocks parse, malformed blocks report clear errors, and no files change.
Validation: Added unit tests for valid, malformed, and empty plans; static review completed because runtime test execution was unavailable in this automation environment.
Risks or assumptions: Parsing is limited to this documented format.
Notes: Use deterministic parsing.

### AUTO-003 — Add deterministic eligible-task selection
Priority: P1
Status: DONE

Goal: Select one TODO task using priority and source order.
Why it matters: Predictable selection makes maintenance reviewable.
Scope: Implement pure selection logic over parsed task records.
Expected files or areas: `src/autonomous_forge/plan.py`, `src/autonomous_forge/cli.py`, tests, README.
Acceptance criteria: P0-to-P3 ordering is enforced and non-TODO tasks are excluded.
Validation: Added unit tests for priority ordering, tie-breaking, non-TODO exclusion, no-task outcomes, unsupported priorities, and CLI `--next` output; static review completed because runtime test execution was unavailable in this automation environment.
Risks or assumptions: Preserve source order as the v1 tie-breaker.
Notes: Selection only reports a result.

### AUTO-004 — Produce a dry-run repository report
Priority: P2
Status: DONE

Goal: Report plan state, selected task, and suggested validation without changing files.
Why it matters: Maintainers need an inspectable starting point.
Scope: Read local plan and state files and print a concise report.
Expected files or areas: CLI, report module, tests, README.
Acceptance criteria: No files are changed and all main result states are clear.
Validation: Added unit and CLI tests for report output, task-state counts, next-task display, and state-file availability; static review completed because runtime test execution was unavailable in this automation environment.
Risks or assumptions: Keep this milestone read-only.
Notes: First user-facing workflow.

### AUTO-005 — Document repository policy format
Priority: P2
Status: DONE

Goal: Define a small readable policy file for future boundaries.
Why it matters: Limits should be clear before later features are added.
Scope: Specify a format and examples only.
Expected files or areas: documentation, example policy, roadmap.
Acceptance criteria: Documentation defines allowed paths, prohibited paths, and approval boundaries.
Validation: Documentation and example consistency reviewed; runtime test execution was unavailable in this automation environment.
Risks or assumptions: Policy semantics stay conservative.
Notes: No runner is added in this task.

### AUTO-006 — Add contributor development guidance
Priority: P3
Status: DONE

Goal: Document local setup, tests, and safe contribution expectations after the package exists.
Why it matters: Clear guidance lowers contributor friction.
Scope: Add a concise contributor guide after AUTO-001.
Expected files or areas: `CONTRIBUTING.md`, README.
Acceptance criteria: Includes setup, tests, task discipline, and safe file handling.
Validation: Manual documentation review completed; runtime test execution was unavailable in this automation environment.
Risks or assumptions: Keep it aligned with implemented tooling.
Notes: Depends on AUTO-001.

## Roadmap v2

### AUTO-007 — Parse repository policy sections
Priority: P1
Status: DONE

Goal: Read `.forge/policy.md` into a small structured policy summary.
Why it matters: The tool should understand its documented safety boundary before later commands rely on it.
Scope: Parse the documented section headings for allowed paths, prohibited paths, approval-required areas, and validation expectations.
Expected files or areas: `src/autonomous_forge/policy.py`, `src/autonomous_forge/cli.py`, tests, README.
Acceptance criteria: Valid example policy parses, missing policy reports a clear read-only error, malformed required sections produce actionable diagnostics, and no repository files are changed.
Validation: Added policy parser and CLI tests; static implementation review completed because runtime test execution was unavailable in this automation environment.
Risks or assumptions: The parser should stay conservative and support only the documented Markdown format.
Notes: Do not enforce changes yet; report only.

### AUTO-008 — Surface policy readiness in dry-run reports
Priority: P1
Status: DONE

Goal: Include policy-file availability and required-section readiness in `forge report`.
Why it matters: Maintainers need to see whether future autonomous work has a readable safety boundary.
Scope: Extend report output to include policy present/missing/malformed status without enforcing path decisions.
Expected files or areas: `src/autonomous_forge/report.py`, `src/autonomous_forge/policy.py`, `src/autonomous_forge/cli.py`, tests, README.
Acceptance criteria: Reports show policy status, keep existing plan/task output stable, and return clear errors for malformed policies.
Validation: Added report CLI support and tests for present, missing, and malformed policy readiness; static implementation review completed because runtime test execution was unavailable in this automation environment.
Risks or assumptions: Do not overstate policy enforcement; this is readiness reporting only.
Notes: Depends on AUTO-007.

### AUTO-009 — Add roadmap structure linting
Priority: P2
Status: DONE

Goal: Add a read-only command that checks roadmap task blocks for required fields and supported values.
Why it matters: A malformed roadmap can cause unsafe or confusing task selection.
Scope: Validate task headings, priority values, status values, and required task fields using the documented format.
Expected files or areas: `src/autonomous_forge/plan.py`, `src/autonomous_forge/cli.py`, tests, README.
Acceptance criteria: `forge lint-plan` exits successfully for the repository roadmap and returns clear diagnostics for malformed examples.
Validation: Added read-only plan linter logic, CLI command, unit tests, CLI tests, and README usage notes. Static implementation review completed because runtime test execution was unavailable in this automation environment.
Risks or assumptions: Keep linting strict enough to catch ambiguity but simple enough to maintain.
Notes: Read-only command only.

### AUTO-010 — Document command output contracts
Priority: P2
Status: DONE

Goal: Document the current CLI commands, exit codes, and stable human-readable output expectations.
Why it matters: Contributors and future automation need predictable behavior before more commands are added.
Scope: Add concise command reference documentation for implemented read-only commands.
Expected files or areas: README, `docs/`, tests if examples are added.
Acceptance criteria: Documentation lists commands, purpose, inputs, outputs, exit-code expectations, and safety limitations.
Validation: Added `docs/COMMANDS.md` covering implemented commands, output patterns, exit-code expectations, and safety limits; linked it from README; static documentation review completed because runtime test execution was unavailable in this automation environment.
Risks or assumptions: Keep docs aligned with implemented behavior only.
Notes: Do not document future commands as complete.

### AUTO-011 — Record local run summaries without execution
Priority: P3
Status: DONE

Goal: Design and document a read-only-safe local run summary format for future use.
Why it matters: Durable execution history is part of the product vision, but write behavior needs careful boundaries.
Scope: Propose the format and add docs only; do not add automatic history-file writes or external command execution.
Expected files or areas: docs, README, roadmap state.
Acceptance criteria: The format captures timestamp, selected task, validation plan, policy status, and changed-files summary placeholder without running external commands.
Validation: Added `docs/RUN_SUMMARIES.md` and README link; static documentation review completed because runtime test execution was unavailable in this automation environment.
Risks or assumptions: Avoid creating automatic history files until explicitly planned.
Notes: Prefer preview output before write behavior.

### AUTO-012 — Preview local run summaries without writing files
Priority: P2
Status: DONE

Goal: Add a read-only command that prints the documented run-summary format.
Why it matters: Maintainers can review the record shape before any command is allowed to persist execution history.
Scope: Build a run-summary preview from the current plan and policy status, including placeholders for validation result, changed files, and commit.
Expected files or areas: `src/autonomous_forge/run_summary.py`, `src/autonomous_forge/cli.py`, tests, README, `docs/COMMANDS.md`, `docs/RUN_SUMMARIES.md`.
Acceptance criteria: `forge run-summary` prints all required fields, supports deterministic timestamp output for tests, does not write files, and documents its safety limits.
Validation: Added run-summary preview module, CLI command, CLI coverage, README usage notes, and command-contract documentation. Static implementation review completed because runtime test execution was unavailable in this automation environment.
Risks or assumptions: Preview output must not imply validation ran or history was persisted.
Notes: No automatic history-file writes, external command execution, diff inspection, commit creation, or network behavior was added.

### AUTO-013 — Document repository health inventory scope
Priority: P2
Status: DONE

Goal: Define the first safe scope for a future read-only repository health inventory.
Why it matters: Inventory behavior should have clear boundaries before it reports repository readiness.
Scope: Add documentation for the signals, output boundaries, and validation expectations of a future inventory command without implementing the command.
Expected files or areas: `docs/HEALTH_INVENTORY.md`, README, roadmap state.
Acceptance criteria: Documentation lists initial file-presence signals, states that the inventory is not enforcement or credential scanning, and keeps behavior read-only and local-only.
Validation: Static documentation review completed against AUTO-013 acceptance criteria; runtime test execution was unavailable in this automation environment.
Risks or assumptions: Do not imply a health score, audit, policy enforcement, or credential scanning before implementation exists.
Notes: Future implementation may add `forge inventory` only after this scope remains acceptable.

### AUTO-014 — Implement read-only repository health inventory
Priority: P2
Status: DONE

Goal: Add a read-only `forge inventory` command based on `docs/HEALTH_INVENTORY.md`.
Why it matters: Maintainers need a quick local view of required maintenance files without implying audit or enforcement.
Scope: Report deterministic file-presence signals for the documented paths only.
Expected files or areas: `src/autonomous_forge/inventory.py`, `src/autonomous_forge/cli.py`, tests, README, `docs/COMMANDS.md`, `docs/HEALTH_INVENTORY.md`.
Acceptance criteria: `forge inventory` prints present/missing signals in stable order, handles repositories without `.ai`, does not read file contents, does not calculate scores, and documents safety limits.
Validation: Static implementation review completed against AUTO-014 acceptance criteria; runtime test execution was unavailable in this automation environment.
Risks or assumptions: Do not imply a health score, audit, policy enforcement, credential scanning, environment inspection, network access, or external command execution.
Notes: Read-only command only.

## Roadmap v3

### AUTO-015 — Detect metadata consistency drift
Priority: P1
Status: DONE

Goal: Add a read-only `forge drift` command that cross-checks plan, state, changelog, and policy files against each other and the repository.
Why it matters: In a self-maintaining repo, drift between metadata and ground truth is the most dangerous failure mode.
Scope: Detect state-vs-plan status mismatches, stale placeholder values, changelog references to nonexistent tasks, and policy paths pointing at missing directories.
Expected files or areas: `src/autonomous_forge/drift.py`, `src/autonomous_forge/cli.py`, tests.
Acceptance criteria: `forge drift` reports categorized signals with severity levels, handles missing optional files gracefully, and does not change any files.
Validation: 13 unit and CLI tests pass; full suite (54 tests) passes with zero regressions. Runtime test execution confirmed.
Risks or assumptions: Drift detection is observational only — no corrections are applied.
Notes: First feature added by a human-AI pair rather than the original autonomous builder.

### AUTO-016 — Capture and replay session context for handoff
Priority: P1
Status: DONE

Goal: Add `forge pause` and `forge resume` commands that capture coding session context and replay it as a structured briefing.
Why it matters: The hardest problem in solo dev is re-loading your brain after an interruption. Session handoff eliminates the ramp-up.
Scope: Auto-capture git state (branch, dirty files, recent commits, stash). Accept mental-context fields (working on, tried, stuck on, half-finished, next steps, notes). Serialize to human-readable Markdown in `.forge/sessions/`. Deserialize and format as a resume briefing.
Expected files or areas: `src/autonomous_forge/session.py`, `src/autonomous_forge/cli.py`, tests, `.gitignore`.
Acceptance criteria: Roundtrip serialize/deserialize preserves all fields, save/load picks the most recent session, CLI commands work end-to-end, session files are gitignored.
Validation: 11 unit and CLI tests pass; full suite (54 tests) passes with zero regressions. Runtime test execution confirmed.
Risks or assumptions: Session files are local working state, not repo metadata. The `pause` command runs `git` as a subprocess — the first external command execution in the project.
Notes: Also implemented as universal Claude Code skills (`/pause`, `/resume`) that synthesize mental context from conversation history rather than requiring CLI flags. The skills are the primary interface; the Python CLI is the engine and fallback.

### AUTO-017 — Generate project context briefing
Priority: P1
Status: DONE

Goal: Add `forge context` that composes task summary, state, policy, drift, and inventory into a single briefing.
Why it matters: Cold-starting agents or checking project status should take one command, not five.
Scope: Compose existing modules (plan, state, policy, drift, inventory) into a unified context report.
Expected files or areas: `src/autonomous_forge/context.py`, `src/autonomous_forge/cli.py`, tests.
Acceptance criteria: One-screen output covering tasks, state, policy, drift, and health. Graceful handling of missing metadata.
Validation: 5 tests pass; full suite passes. Runtime confirmed.
Risks or assumptions: Composing existing modules only — no new data sources.
Notes: Also created `/forge` Claude Code skill as the universal status command.

### AUTO-018 — Scaffold forge metadata into any repository
Priority: P1
Status: DONE

Goal: Add `forge init` that creates `.ai/` and `.forge/` metadata files in any repo.
Why it matters: Without init, adopting the forge requires manually creating 5+ files. This makes it a one-command setup.
Scope: Create plan, state, changelog, decisions, and policy templates. Append gitignore. Skip existing files.
Expected files or areas: `src/autonomous_forge/init.py`, `src/autonomous_forge/cli.py`, tests.
Acceptance criteria: Creates all metadata files, skips existing ones, appends to gitignore, uses project name in templates.
Validation: 6 tests pass; full suite passes. Runtime confirmed.
Risks or assumptions: Templates are conservative defaults — users should customize policy for their project.
Notes: First command that creates files outside `.forge/sessions/`.

### AUTO-019 — Validate changed files against policy boundaries
Priority: P1
Status: DONE

Goal: Add `forge diff-check` that validates git-changed files against policy allowed/prohibited paths.
Why it matters: This is the safety gate — before any autonomous commit, changes must comply with policy.
Scope: Read git diff (staged or all), match each file against policy patterns, report violations.
Expected files or areas: `src/autonomous_forge/diffcheck.py`, `src/autonomous_forge/cli.py`, tests.
Acceptance criteria: Detects prohibited files, flags files outside allowed paths, reports cleanly with no changes.
Validation: 9 tests pass; full suite passes. Runtime confirmed.
Risks or assumptions: Runs `git` as a subprocess. Pattern matching uses `fnmatch` — may not cover all glob edge cases.
Notes: Prohibited files are flagged exclusively (no duplicate "not-allowed" signal).

### AUTO-020 — Run validation commands and report results
Priority: P1
Status: DONE

Goal: Add `forge validate` that runs the test suite and reports structured pass/fail results.
Why it matters: This is the first real execution step — the forge can now verify its own changes.
Scope: Extract validation command from policy (or use default), run it, capture output, report results.
Expected files or areas: `src/autonomous_forge/validate.py`, `src/autonomous_forge/cli.py`, tests.
Acceptance criteria: Runs commands, reports pass/fail with output, handles timeouts, works cross-platform.
Validation: 8 tests pass; full suite (81 tests) passes. Runtime confirmed.
Risks or assumptions: Runs external commands via subprocess. Handles PYTHONPATH portably. Timeout defaults to 300s.
Notes: Exit code 0 on pass, 1 on fail. The first forge command that executes external processes.

### AUTO-021 — Execute one autonomous improvement cycle
Priority: P0
Status: DONE

Goal: Add `forge run` that ties together task selection, validation, diff-check, drift detection, and run recording into a single command.
Why it matters: This is the autonomous loop — the command that makes the forge actually autonomous. It replaces manual orchestration of five separate commands with one cycle.
Scope: Select next eligible task, check for drift blockers, validate changed files against policy, run test suite, record structured outcome to `.forge/runs/`.
Expected files or areas: `src/autonomous_forge/run.py`, `src/autonomous_forge/cli.py`, tests.
Acceptance criteria: Selects task, blocks on prohibited changes or error-level drift, runs validation (with dry-run and no-validate modes), saves run outcomes, CLI returns exit code 1 when blocked.
Validation: 15 tests pass; full suite (96 tests) passes with zero regressions. Runtime confirmed.
Risks or assumptions: Runs git and subprocess for validation. Does not auto-commit — that remains a human decision.
Notes: Supports `--dry-run`, `--no-validate`, `--no-save`, `--cmd` override. Exit 0 on success, 1 on blocked.

### AUTO-022 — Bridge plan tasks to Forgejo issues
Priority: P1
Status: DONE

Goal: Add `forge sync` that pushes AUTO-xxx task status to Forgejo issues, creating a one-way bridge from the local plan to the project management layer.
Why it matters: The forge's local plan file and Forgejo issues were parallel tracking systems with no connection. This bridges them so humans see task progress where they expect it.
Scope: Auto-detect repo from git remote. Create issues with title prefix `[AUTO-xxx]`. Apply status/priority labels. Map roadmap versions to milestones. Close DONE issues, reopen TODO issues. Ensure labels and milestones exist. Persist no local state beyond the API calls.
Expected files or areas: `src/autonomous_forge/sync.py`, `src/autonomous_forge/cli.py`, tests.
Acceptance criteria: Dry-run mode shows planned actions without API calls. Live sync creates/updates issues with correct labels and milestones. Re-running is idempotent (up-to-date tasks are skipped). CLI returns exit code 1 on errors.
Validation: 14 tests pass; full suite (110 tests) passes with zero regressions. Live sync confirmed — 21 issues created, 3 milestones auto-generated, all DONE tasks closed.
Risks or assumptions: Requires network access and `FORGEJO_TOKEN`. Uses Python stdlib `urllib` (zero dependencies). Only syncs to `forgejo.familytechlab.com` remotes.
Notes: Also created `/forge-sync` Claude Code skill. Plan file remains the source of truth. Forgejo is the mirror.

### AUTO-023 — Safe auto-commit with pre-flight checks
Priority: P1
Status: DONE

Goal: Add `forge commit` that runs policy diff-check and validation before committing, ensuring every commit passes safety gates.
Why it matters: `forge run` reports "ready to commit" but the commit itself was still manual. This closes the loop with safety baked in.
Scope: Pre-flight checks (diff-check against policy, run validation). Auto-generate commit message from current task. `--check-only` mode for dry-run. Block on prohibited files or validation failure.
Expected files or areas: `src/autonomous_forge/commit.py`, `src/autonomous_forge/cli.py`, tests.
Acceptance criteria: Blocks on prohibited files, blocks on validation failure, auto-generates message from task, `--check-only` runs checks without committing, CLI returns exit code 1 when blocked.
Validation: 14 tests pass; full suite (124 tests) passes with zero regressions. Runtime confirmed.
Risks or assumptions: Runs git commit as subprocess. Does not push — that remains a separate decision.
Notes: Supports `--check-only`, `--no-validate`, `-m` message override, `--cmd` validation override.

## Future Ideas

- Hash-linked local run reports.
- Optional issue import.
- Cross-repo session handoff aggregation (resume across multiple projects).
- `forge watch` — daemon mode that periodically checks repo state.

## Do Not Change Without Explicit Human Approval

- Remote and branch settings.
- Repository visibility and access controls.
- Production infrastructure.
- Features that run external commands.
- Features that change repository files outside documented safe paths.
- Credential handling, telemetry, analytics, billing, or deployment behavior.
