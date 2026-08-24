# Autonomous Forge Roadmap

## Product vision

Autonomous Forge helps a repository keep a clear improvement plan, choose one small task, check the result, and record what happened.

## Product scope and non-goals

The first product remains a local Python command-line tool. It reads repository files, reports safe next actions, and keeps durable project memory. It is not a hosted platform, dashboard, autonomous executor, deployment system, or permission-management tool.

## Current architecture

The project has two interfaces: a Python CLI (`forge`) and Claude Code skills (`/pause`, `/resume`). The Python package lives under `src/autonomous_forge` with tests under `tests/`. See `docs/COMMANDS.md` for the full, current command reference (`forge --help` also lists every subcommand) — the roadmap task list above is the source of truth for what's been added. The Claude Code skills live in global config (`~/.claude/commands/`) and work in any repo. Session handoff files are stored in `.forge/sessions/` (gitignored). The project uses zero runtime dependencies; several commands shell out to `git`, and `forge sync` makes Forgejo API calls via stdlib `urllib`.

## Current implementation status

Roadmaps v1 through v6 are complete (47 tasks). Roadmap v6 fixed the long-standing plan-lint Notes gap, resolved an orphaned duplicate doc, added `forge metrics --json`, documented a CI recipe, and added `forge revert`. All 329 tests pass at runtime.

## Technical debt

None currently tracked. Prior debt (run summary persistence, missing `docs/COMMANDS.md` coverage for `drift`/`pause`/`resume`/`push`) was resolved in Roadmap v3.

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

### AUTO-024 — View run history
Priority: P2
Status: DONE

Goal: Add `forge log` to view past run outcomes from `.forge/runs/` and add `__main__.py` for `python -m autonomous_forge` support.
Why it matters: Runs are being recorded but there was no way to review them. The log closes the observability loop.
Scope: Parse run summary files, list newest-first with limit, format as a scannable log with optional verbose mode.
Expected files or areas: `src/autonomous_forge/log.py`, `src/autonomous_forge/__main__.py`, `src/autonomous_forge/cli.py`, tests.
Acceptance criteria: Lists runs newest-first, supports `--limit` and `--verbose`, handles missing runs dir gracefully, CLI wired up.
Validation: 11 tests pass; full suite (135 tests) passes with zero regressions. Runtime confirmed.
Risks or assumptions: Parses run summary Markdown files — format changes could break parsing.
Notes: First command to read `.forge/runs/` output back; also the first task to add `__main__.py` so `python -m autonomous_forge` works alongside the console script.

### AUTO-025 — Full autonomous pipeline command
Priority: P0
Status: DONE

Goal: Add `forge pipeline` that chains run -> commit -> sync into a single command with explicit opt-in at each stage.
Why it matters: The autonomous loop required running three commands manually. This is the "one button" mode.
Scope: Chain run, commit, and sync stages. Stop at each gate (blocked, validation failure, no changes). Require `--commit` and `--sync` flags for opt-in. Save run outcome automatically.
Expected files or areas: `src/autonomous_forge/pipeline.py`, `src/autonomous_forge/cli.py`, tests.
Acceptance criteria: Stops on block/failure at any stage, skips commit without `--commit`, skips sync without `--sync`, formats concise multi-stage report.
Validation: 6 tests pass; full suite (141 tests) passes with zero regressions. Runtime confirmed.
Risks or assumptions: Commit and sync are opt-in — pipeline without flags is equivalent to `forge run` with auto-save.
Notes: Later grew a `--push` stage (AUTO-033) between commit and sync, and hash-linking to run reports (AUTO-034) — this task established the stage-gating pattern (stop at any gate, each escalation opt-in) that both reused.

### AUTO-026 — Mark task status from CLI
Priority: P0
Status: DONE

Goal: Add `forge mark` to update a task's status in the plan file from the command line.
Why it matters: Previously required manual markdown editing. This closes the loop — the forge can now complete a task and mark it done without human file edits.
Scope: Parse the plan file, find the target task, rewrite its Status line, preserve everything else.
Expected files or areas: `src/autonomous_forge/mark.py`, `src/autonomous_forge/cli.py`, tests.
Acceptance criteria: Updates status in-place, preserves other tasks, rejects invalid statuses, handles missing plan/task.
Validation: 14 tests pass; full suite 161 tests pass. Runtime confirmed.
Risks or assumptions: Only mutates the Status line — all other fields untouched.
Notes: Paired with `forge plan add` (AUTO-029), this closes the full task lifecycle (create, select, execute, mark, sync) from the CLI with no manual Markdown editing required anywhere.

### AUTO-027 — Quick at-a-glance status
Priority: P1
Status: DONE

Goal: Add `forge status` — a compact one-screen summary showing branch, dirty files, task counts, next task, last run, and policy presence.
Why it matters: `forge report` is verbose. Day-to-day you want a 4-line glance.
Scope: Read git branch/dirty count, plan task counts, last run timestamp, policy presence.
Expected files or areas: `src/autonomous_forge/status.py`, `src/autonomous_forge/cli.py`, tests.
Acceptance criteria: Shows branch, dirty count, task breakdown, next task, last run, policy status. Handles missing plan gracefully.
Validation: 6 tests pass; full suite 161 tests pass. Runtime confirmed.
Risks or assumptions: Runs `git` as subprocess for branch/dirty info. No network calls.
Notes: Complements the more verbose `forge report` — this is the 4-line daily glance, `forge report` is the full dry-run summary.

### AUTO-028 — Combined verification check
Priority: P1
Status: DONE

Goal: Add `forge check` — run lint, drift, diff-check, and validation in one command.
Why it matters: Previously required running 4 separate commands to verify repo health. This is the "are we good?" command.
Scope: Run lint-plan, drift detection, diff-check against policy, and validation. Report pass/fail for each. Return non-zero if any fail.
Expected files or areas: `src/autonomous_forge/check.py`, `src/autonomous_forge/cli.py`, tests.
Acceptance criteria: Runs all four checks, reports each independently, exits 0 only if all pass. Supports `--no-validate` to skip tests.
Validation: 10 tests pass; full suite 171 tests pass. Runtime confirmed.
Risks or assumptions: None. Also fixed SKIPPED status not being in _SUPPORTED_STATUSES.
Notes: The "are we good?" command — later reused as the core of `forge watch`'s polling loop (Roadmap v4) and referenced directly by `forge doctor`'s design discussion (Roadmap v5).

### AUTO-029 — Add tasks to plan from CLI
Priority: P0
Status: DONE

Goal: Add `forge plan add` to create new task blocks in the plan file from the CLI, auto-incrementing IDs.
Why it matters: Closes the creation loop — the forge can now create, select, execute, mark, and sync tasks entirely from CLI. No manual markdown editing needed.
Scope: Parse existing IDs, compute next ID, build properly formatted task block, insert before Future Ideas section.
Expected files or areas: `src/autonomous_forge/planadd.py`, `src/autonomous_forge/cli.py`, tests.
Acceptance criteria: Auto-increments IDs, inserts before Future Ideas, preserves existing content, accepts priority/scope/files/acceptance/notes.
Validation: 14 tests pass; full suite 192 tests pass. Runtime confirmed.
Risks or assumptions: Only appends — no task reordering or section targeting.
Notes: Closes the creation loop — paired with `forge mark` (AUTO-026), the full task lifecycle is now CLI-driven. Its insertion logic (insert before `## Future Ideas`, auto-increment IDs) was reused directly by `forge sync --import-orphans` (Roadmap v5, AUTO-042).

### AUTO-030 — Aggregate run history metrics
Priority: P1
Status: DONE

Goal: Add `forge metrics` to show aggregate stats from run history — total runs, pass rate, unique tasks, violations, drift.
Why it matters: Gives visibility into the health and productivity of the autonomous loop over time.
Scope: Read all run files, compute counts and pass rate, format as concise report.
Expected files or areas: `src/autonomous_forge/metrics.py`, `src/autonomous_forge/cli.py`, tests.
Acceptance criteria: Shows total runs, passed/failed/blocked counts, pass rate percentage, unique tasks, cumulative files/violations/drift.
Validation: 7 tests pass; full suite 192 tests pass. Runtime confirmed.
Risks or assumptions: Uses existing log module for run parsing.
Notes: Reuses `log.py`'s existing run-file parsing rather than duplicating it. Roadmap v6 (AUTO-045) plans a `--json` export alongside the current human-readable report.

### AUTO-031 — Task filtering
Priority: P1
Status: DONE

Goal: Add `--status` and `--priority` filters to `forge tasks` for focused task views.
Why it matters: With 30+ tasks, unfiltered output is noisy. Filters let you ask "what's TODO?" or "what's P0?".
Scope: Add filter arguments to tasks parser, apply in _print_tasks. Case-insensitive matching.
Expected files or areas: `src/autonomous_forge/cli.py`, tests.
Acceptance criteria: Filter by status, priority, or both. Case-insensitive. Shows "No matching" when empty.
Validation: 4 tests pass; full suite 203 tests pass. Runtime confirmed.
Risks or assumptions: None.
Notes: Purely additive CLI flags on the existing `forge tasks` command — no new module.

### AUTO-032 — JSON export
Priority: P1
Status: DONE

Goal: Add `forge export` to output forge state as JSON for programmatic integration.
Why it matters: Enables CI/CD pipelines, dashboards, and external tools to consume forge state.
Scope: Export plan tasks, counts, next task, policy status, and optionally run history as JSON.
Expected files or areas: `src/autonomous_forge/export.py`, `src/autonomous_forge/cli.py`, tests.
Acceptance criteria: Valid JSON output with version, plan, tasks, counts, next_task, policy. Optional --runs flag.
Validation: 7 tests pass; full suite 203 tests pass. Runtime confirmed.
Risks or assumptions: JSON schema is versioned for future compatibility.
Notes: `src/autonomous_forge/export.py` — a separate module from `forge metrics`, exporting broader forge state (plan, tasks, counts, policy) rather than just run-history aggregates.

### AUTO-033 — Push stage in pipeline
Priority: P0
Status: DONE

Goal: Add a `--push` stage to `forge pipeline` that pushes local commits to the git remote after a successful commit and before Forgejo sync.
Why it matters: `forge sync` only updated Forgejo issue labels/state — it never ran `git push`. Autonomous sessions accumulated local-only commits with nothing pushing them upstream, so a repo could silently drift dozens of commits behind origin.
Scope: New `src/autonomous_forge/push.py` module (`execute_push`, `format_push_result`); wired as a stage between commit and sync in `pipeline.py`; new `--push` CLI flag on `forge pipeline`.
Expected files or areas: `src/autonomous_forge/push.py`, `src/autonomous_forge/pipeline.py`, `src/autonomous_forge/cli.py`, `docs/COMMANDS.md`, tests.
Acceptance criteria: `forge pipeline --commit --push` pushes HEAD to the current branch's remote after commit; skips the push call if already up to date; fails loudly (no rebase/merge/force-push) on a rejected/diverged push and stops the pipeline before sync runs.
Validation: 10 new tests pass (`test_push.py`, `test_pipeline.py`); full suite 216 tests pass.
Risks or assumptions: Push always targets `origin` and the current branch's own name (no cross-branch push). Divergence must be resolved manually — the tool does not attempt automatic conflict resolution.
Notes: `push.py`'s `execute_push` was later reused as-is for the standalone `forge push` command (Roadmap v4), independent of task selection or commit state.

## Roadmap v4

### AUTO-034 — Hash-linked local run reports
Priority: P2
Status: DONE

Goal: Link each local run report to the git commit hash it produced, so run history in `.forge/runs/` can be cross-referenced against `git log`.
Why it matters: Run reports currently record task/validation/drift info but not which commit (if any) resulted from that run, making it hard to trace "which run produced commit X" during an audit.
Scope: Add an optional `commit_hash` field to the run report schema, populated when a pipeline run produces a commit in the same invocation. `forge log` displays the hash when present. Run reports saved before this change (no field) must still load and print without error.
Expected files or areas: `src/autonomous_forge/run.py`, `src/autonomous_forge/pipeline.py`, `src/autonomous_forge/log.py`, tests.
Acceptance criteria: A `forge pipeline --commit` run's saved report includes the resulting commit hash; `forge log` shows it; run reports without the field still load and print without error.
Validation: 6 new tests pass (`test_run.py`, `test_log.py`, `test_pipeline.py`); full suite 224 tests pass. Runtime confirmed.
Risks or assumptions: Only applies when a commit actually happens in the same pipeline invocation — a standalone `forge run` (no `--commit`) report has no hash, which is expected, not a bug.
Notes: Commit hash is appended as a trailing `Commit:` line after the run report is saved, since the hash isn't known until after `execute_commit` runs.

### AUTO-035 — Read-only Forgejo orphan-issue report
Priority: P2
Status: DONE

Goal: Add a read-only report that lists Forgejo issues with no matching `[AUTO-###]` task in the current plan, so manually-created issues can be spotted and reconciled by a human.
Why it matters: `forge sync` is intentionally one-way (plan -> Forgejo); issues created directly in Forgejo are invisible to the tool and never show up in `forge tasks` or `forge status`. Surfacing them prevents silently orphaned work — this is exactly the failure mode that motivated AUTO-033/the PENDING/COMPLETE status fix, applied to issues instead of statuses.
Scope: New `--report-orphans` flag on `forge sync` that lists open Forgejo issues lacking an `[AUTO-###]` prefix match against current plan tasks. Read-only — makes no write API calls and does not modify the plan file. Explicitly out of scope: auto-generating plan task stubs from orphan issues; a human decides what, if anything, to add.
Expected files or areas: `src/autonomous_forge/sync.py`, `src/autonomous_forge/cli.py`, tests.
Acceptance criteria: `forge sync --report-orphans` lists issue number and title for every open issue with no `[AUTO-###]` match; exits 0 with "No orphan issues" when none found; issues no write requests to the Forgejo API.
Validation: 16 new tests pass (`test_sync.py`), mocking the Forgejo client; full suite 240 tests pass. Runtime confirmed.
Risks or assumptions: Read-only by design — writing plan tasks from Forgejo issues is deliberately out of scope to preserve "the plan is the source of truth."
Notes: Orphan detection matches any `AUTO-###` substring in the issue title (bracketed or unbracketed) against current plan task IDs — an issue referencing a task ID that was later removed from the plan counts as an orphan too, not just issues with no AUTO tag at all.

### AUTO-036 — Cross-repo session handoff aggregation
Priority: P2
Status: DONE

Goal: Add a `--roots` option to `forge resume` that scans the latest session file in each of several repo roots and prints a combined multi-project briefing.
Why it matters: `forge pause`/`forge resume` already capture per-repo handoff; a user working across several forge-enabled projects has to `cd` into each one and run `forge resume` separately to see what's pending.
Scope: New `--roots` argument (comma-separated paths) on the resume command; for each root, load its newest `.forge/sessions/session-*.md` (reusing existing session parsing) and print a short summary per project. No cross-repo git operations beyond what `forge resume` already does per-repo.
Expected files or areas: `src/autonomous_forge/session.py`, `src/autonomous_forge/cli.py`, tests, `docs/COMMANDS.md`.
Acceptance criteria: `forge resume --roots a,b,c` prints one section per root with its most recent session summary; a root with no session file is reported as such, not treated as an error; single-repo `forge resume` behavior is unchanged.
Validation: 4 new tests pass (`test_session.py`) with fixture session files across multiple `tmp_path` roots; full suite 244 tests pass. Runtime confirmed.
Risks or assumptions: Assumes each listed root is a local, already forge-initialized path; does not fetch or clone remote repos.
Notes: `--roots` overrides `--root` when both are passed rather than erroring, matching the "explicit flag wins" pattern used elsewhere in the CLI.

### AUTO-037 — `forge watch` periodic check mode
Priority: P3
Status: DONE

Goal: Add `forge watch [--interval SECONDS] [--once]` that periodically re-runs `forge check` (lint + drift + diff-check + validation) and prints results, exiting cleanly on Ctrl+C.
Why it matters: Drift and policy issues are currently only caught when someone remembers to run `forge check` manually; a lightweight foreground watcher catches regressions between sessions without requiring external cron/scheduler setup.
Scope: A polling loop around the existing `execute_check` — read-only, no commits, no network calls, no autonomous fixes. `--once` runs a single check-and-exit (for scripting/testing). `--interval` defaults to a sane value (e.g. 300 seconds). No daemonization or PID files — foreground process only, matching the project's stated non-goal of being "a hosted platform... autonomous executor."
Expected files or areas: `src/autonomous_forge/watch.py`, `src/autonomous_forge/cli.py`, tests, `docs/COMMANDS.md`.
Acceptance criteria: `forge watch --once` runs exactly one check cycle and exits with `forge check`'s exit code; `forge watch --interval N` loops, printing a check report every N seconds, until interrupted; Ctrl+C exits cleanly with code 0.
Validation: 7 new tests pass (`test_watch.py`), with mocked sleep/print/`execute_check` and no real sleeping; full suite 251 tests pass. Runtime confirmed via `forge watch --once` against this repo.
Risks or assumptions: Explicitly read-only — does not trigger `forge pipeline` or any commit/push. A backgrounded/daemonized mode, if ever wanted, is a separate task requiring explicit human approval given the project's non-goals.
Notes: `--once` and the interrupted multi-cycle loop have different exit-code semantics on purpose — `--once` returns the check's actual pass/fail code (for scripting), while Ctrl+C on a running loop always returns 0 (interruption is not itself a failure).

## Roadmap v5

### AUTO-038 — Diagnose environment issues before a run
Priority: P1
Status: DONE

Goal: Add `forge doctor` that checks for common silent-failure causes before a run: missing FORGEJO_TOKEN, git remote URL mismatch against the configured Forgejo repo, git/Python availability, and missing required files (.ai/, .forge/policy.md).
Why it matters: This project has already hit two silent-failure classes (a 301-redirecting git remote, missing plan Notes fields) that went unnoticed until something downstream broke. A one-command diagnostic catches these before a run, not after.
Scope: Read-only diagnostic checks; print PASS/FAIL per check with a short remediation hint. No fixes applied automatically.
Expected files or areas: src/autonomous_forge/doctor.py, src/autonomous_forge/cli.py, tests, docs/COMMANDS.md
Acceptance criteria: Detects missing FORGEJO_TOKEN, detects git remote/repo-name mismatch (the underscore/hyphen class of bug hit in Roadmap v4), reports a clean pass when the environment is healthy, exits 1 on any failed check.
Validation: 10 new tests pass (`test_doctor.py`); full suite 263 tests pass. Runtime confirmed via `forge doctor` against this repo (ALL PASSED).
Risks or assumptions: The repo-reachability check makes one GET call to the Forgejo API — the only network action in an otherwise read-only command. Skipped (not failed) when no token or remote is detected, since it cannot run without both.
Notes: Motivated directly by two silent-failure incidents already hit in this project: a 301-redirecting git remote and missing plan Notes fields going unnoticed for many tasks.

### AUTO-039 — Repo-level config defaults
Priority: P1
Status: DONE

Goal: Add a `.forge/config.toml` (or similar) read by all commands, so repo-level defaults for --plan, --policy, --root, and --cmd stop needing to be passed on every invocation.
Why it matters: Every command invocation was repeating the same --plan/--policy/--cmd paths for a given repo. A one-time repo-level default removes that repetition without weakening the "explicit flag always wins" safety property.
Scope: New optional config file, parsed once and merged with explicit CLI flags (explicit flags always win). forge init should scaffold a default config alongside existing templates.
Expected files or areas: src/autonomous_forge/config.py, src/autonomous_forge/cli.py, src/autonomous_forge/init.py, tests, docs/COMMANDS.md
Acceptance criteria: Commands use config-file values when a flag is omitted, explicit flags override config values, missing config file falls back to current hardcoded defaults with no behavior change.
Validation: 22 new tests pass (`test_config.py` + updated `test_init.py`); full suite 274 tests pass. Runtime confirmed: a `.forge/config.toml` pointing `plan` at a different file was picked up with no `--plan` flag, and an explicit `--plan` flag correctly overrode it.
Risks or assumptions: `--root` was scoped out of config values (it's needed to locate the config file itself, so it can't be sourced from it) — only `--plan`, `--policy`, and every `--cmd`-family flag are covered. Uses a minimal hand-written parser, not stdlib `tomllib`, since this project supports Python 3.10+ and `tomllib` requires 3.11+.
Notes: Also normalized six legacy commands (`tasks`, `lint-plan`, `report`, `policy`, `run-summary`, `drift`) that previously hardcoded `--plan`/`--policy` defaults directly in argparse — they now default to `None` like every other command, with the hardcoded path applied as a fallback at dispatch, so config defaults can actually reach them.

### AUTO-040 — Prevent concurrent forge run/pipeline collisions
Priority: P1
Status: DONE

Goal: Add a lightweight lock file so two concurrent `forge run`/`forge pipeline` invocations against the same repo cannot double-commit or race.
Why it matters: Nothing previously stopped a human and an agent, or two agent sessions, from running `forge run`/`forge pipeline` against the same repo at the same time — a realistic scenario now that the pipeline is used both interactively and by autonomous loops. Without a lock, two concurrent invocations could both select the same task, both commit, or interleave git operations.
Scope: Acquire a .forge/.lock file (PID + timestamp) at the start of run/pipeline, release on exit (including on error), and fail fast with a clear message if a live lock is already held.
Expected files or areas: src/autonomous_forge/lock.py, src/autonomous_forge/run.py, src/autonomous_forge/pipeline.py, tests, docs/COMMANDS.md
Acceptance criteria: A second concurrent invocation fails fast with a clear 'already running (pid X)' message instead of racing; a stale lock (process no longer alive) is detected and cleared automatically; normal single-invocation runs are unaffected.
Validation: 18 new tests pass (`test_lock.py` + additions to `test_run.py`/`test_pipeline.py`); full suite 289 tests pass. Runtime confirmed against this repo with a genuinely live Windows PID: a second `forge run` correctly reported `BLOCKED: already running (pid N, ...)` and exited 1 without touching the lock; after killing that process, the next `forge run` detected the stale lock, cleared it, and completed normally (exit 0), and a normal run leaves no lock file behind.
Risks or assumptions: `os.kill(pid, 0)` is unsafe as a liveness probe on Windows — passing signal 0 there maps to `TerminateProcess(handle, 0)`, which would actually kill the process instead of just checking it. Windows uses `ctypes`/`OpenProcess` instead, which only queries. `execute_pipeline` acquires the lock once for the whole pipeline (run+commit+push+sync) and calls `execute_run` internally with `use_lock=False`, rather than each stage double-acquiring.
Notes: Guards against the realistic case of a human and an agent (or two agent sessions) running against the same repo at once — currently nothing prevents this. `.forge/.lock` is gitignored, same as `.forge/sessions/` and `.forge/runs/`.

### AUTO-041 — Auto-append completed tasks to the changelog
Priority: P2
Status: DONE

Goal: Have `forge commit`/`forge pipeline` append a line to .ai/AUTONOMOUS_CHANGELOG.md when a task's status flips to DONE, so the changelog stops silently drifting from the plan.
Why it matters: The changelog was being maintained by hand and silently stopped after AUTO-032 — nothing from AUTO-033 through AUTO-040 was ever recorded there, even though all of it landed and was synced to Forgejo. Automating the append closes that drift permanently instead of relying on someone remembering.
Scope: On successful commit of a task that is now DONE, append a dated one-line changelog entry (task ID, title, commit hash). Do not rewrite or reorder existing changelog content.
Expected files or areas: src/autonomous_forge/changelog.py, src/autonomous_forge/commit.py, src/autonomous_forge/pipeline.py, tests, docs/COMMANDS.md
Acceptance criteria: A completed task's commit appends exactly one new changelog line with task ID, title, and commit hash; non-DONE-flipping commits do not touch the changelog; existing changelog content is preserved verbatim.
Validation: 12 new tests pass (`test_changelog.py` + real-git integration tests in `test_commit.py`); full suite 301 tests pass. Runtime confirmed against this repo — this very commit's changelog entry was generated by the feature it implements.
Risks or assumptions: The commit hash is deliberately omitted from the entry — it doesn't exist yet at append time (the append happens before `git commit` runs, so the line lands in the same commit). The task ID is searchable via `git log --grep=AUTO-###` instead. Decided explicitly with the user rather than assumed: the alternative (a second automatic follow-up commit carrying the real hash) was rejected as too large a behavior change — see plan discussion; a formal DEC entry was not filed since this was a same-session, low-stakes format choice rather than a standing policy decision.
Notes: The changelog file already exists in the metadata scaffold but nothing currently writes to it automatically — this closes that gap, mirroring how forge mark closes the manual-status-edit gap. `find_newly_done_tasks` compares the working-tree plan against the plan's content at HEAD via `git show`, so it only fires when a task's Status line actually changed to DONE in this commit, not on every commit that happens to have DONE tasks in history. Caught and fixed a real bug from this task's own first dogfooded run: `_read_head_text` originally used `subprocess.run(text=True)` without an explicit encoding, which decodes using the OS locale default — cp1252 on this Windows box — silently mangling the plan file's UTF-8 em-dashes instead of raising, which broke every task heading regex and made `git show HEAD:...` appear to contain zero tasks, so every already-DONE task looked "newly done." Fixed by decoding as bytes and calling `.decode("utf-8")` explicitly. Caught before push by inspecting the first real commit's diff rather than trusting the "Changelog updated: AUTO-001, AUTO-002, ..." output at face value — always worth checking commands emit output where changes are directly observable.

### AUTO-042 — Import orphan Forgejo issues into the plan as AUTO-xxx stubs
Priority: P2
Status: DONE

Goal: Add `forge sync --import-orphans` that converts current orphan Forgejo issues (from AUTO-035's --report-orphans) into new AUTO-xxx task stubs appended to the plan file, in one explicit, human-triggered run.
Why it matters: Issues filed directly in Forgejo (bug reports, ideas) had no path into the plan short of a human manually re-typing them with `forge plan add`. This closes that gap while keeping a human review point, completing Roadmap v5.
Scope: Reuse the existing orphan-issue detection from AUTO-035. For each orphan issue, append a new AUTO-xxx task block (title from issue title, Notes referencing the source issue number/URL, Status TODO, Priority P2 default) before Future Ideas, matching forge plan add's existing insertion behavior. No per-issue prompt; the human reviews the resulting plan diff before committing it. --report-orphans stays read-only and unchanged; --import-orphans is a separate, opt-in flag.
Expected files or areas: src/autonomous_forge/sync.py, src/autonomous_forge/planadd.py, src/autonomous_forge/cli.py, tests, docs/COMMANDS.md
Acceptance criteria: Running --import-orphans creates one AUTO-xxx stub per current orphan issue with correct auto-incremented IDs, each stub's Notes references the source Forgejo issue number; --report-orphans and plain --dry-run behavior are unaffected; re-running after a previous import does not duplicate stubs for issues already imported (idempotent against issues already referenced by an AUTO-xxx Notes field).
Validation: 12 new tests pass (`TestExecuteImportOrphans`/`TestFormatImportResult` in `test_sync.py` + a CLI test); full suite 312 tests pass. Runtime confirmed against this repo with `--report-orphans` and `--import-orphans` (no live orphans currently exist, so both correctly reported none — write-path and idempotency verified via the mocked test suite instead of creating throwaway issues on the live tracker).
Risks or assumptions: Idempotency is detected via a Notes-field text match (`Forgejo issue #<N>`) rather than a structured field — if a human hand-edits that Notes text, re-running --import-orphans could re-import the same issue. Acceptable given this is explicit and human-reviewed, not autonomous.
Notes: See DEC-010 in .ai/DECISIONS.md: this is an explicit, human-triggered partial reversal of AUTO-035's read-only-only stance — the human still reviews the plan diff before committing, preserving the plan as source of truth. Completes Roadmap v5 (AUTO-038 through AUTO-042, all DONE).

## Roadmap v6

### AUTO-043 — Fix missing Notes field on AUTO-024 through AUTO-033
Priority: P3
Status: DONE

Goal: Add a Notes line to each of the 10 task blocks (AUTO-024 through AUTO-033) that forge lint-plan has been flagging as missing the required Notes field since they were created.
Why it matters: forge lint-plan/forge check have shown these 10 diagnostics on every single run across all of Roadmap v4 and v5, training reviewers to skim past lint output instead of trusting it as genuinely green.
Scope: Edit only the Notes: line of each of the 10 task blocks; no other content changes. A short factual note per task (what it added / any follow-up) is sufficient — matches the style already used on every other DONE task.
Expected files or areas: .ai/AUTONOMOUS_PLAN.md
Acceptance criteria: forge lint-plan reports zero diagnostics; all 10 tasks retain their original Priority/Status/Goal/etc. unchanged.
Validation: `forge lint-plan` now reports "Plan lint: ok" — the first time in this project's history. Full suite unaffected (no code changed, plan-file-only edit).
Risks or assumptions: None.
Notes: Pure cleanup, flagged repeatedly by forge check/forge lint-plan across the whole v4 and v5 roadmap without ever being fixed.

### AUTO-044 — Remove duplicate workflow-reference.html
Priority: P3
Status: DONE

Goal: Delete the duplicate workflow-reference.html at the repo root; the canonical copy is docs/workflow-reference.html.
Why it matters: Untracked, uncommitted duplicate files sitting in the working tree are exactly the kind of stray state that erodes trust in `git status` — every session for weeks noted it in "cruft, not real work" without anyone actually resolving it.
Scope: Confirm docs/workflow-reference.html is the canonical, up-to-date copy, then delete the root-level duplicate. No content changes to the canonical file.
Expected files or areas: workflow-reference.html (delete)
Acceptance criteria: workflow-reference.html no longer exists at repo root; docs/workflow-reference.html is unchanged and still referenced correctly from anywhere that links to it.
Validation: Full suite unaffected (312 tests pass) — no code touched. Confirmed both copies were byte-identical before deleting the root one.
Risks or assumptions: Discovered mid-task that *neither* copy was ever actually committed to git, and nothing in the repo linked to it — the original "duplicate" framing undersold the actual state. Resolved with the user: commit the canonical docs/ copy for real (it was a genuine, well-built reference page, just orphaned), update its hardcoded stats (24→27 commands, 203→312 tests, 32→43 tasks shipped) since they were stale enough to be actively misleading, and add a README link describing it as a curated highlights reference (not exhaustive — points to docs/COMMANDS.md for the full command list).
Notes: Leftover cleanup item first flagged in a much earlier session, still not done as of Roadmap v5.

### AUTO-045 — Add forge metrics --json export
Priority: P2
Status: DONE

Goal: Add a --json flag to forge metrics that prints the same aggregate run-history stats as machine-readable JSON, for external dashboards or scripting.
Why it matters: `forge export` already versions its JSON output for broader forge state, but run-history metrics had no machine-readable path at all — anything scripting against pass rate/drift/violations had to scrape the human-readable text report.
Scope: Reuse the existing compute_metrics() data; add a JSON serialization path alongside the current human-readable format_metrics(). No new data collected — same fields, different output format.
Expected files or areas: src/autonomous_forge/metrics.py, src/autonomous_forge/cli.py, tests, docs/COMMANDS.md
Acceptance criteria: forge metrics --json prints valid JSON with the same fields as the human-readable report (total runs, pass/fail/blocked counts, pass rate, unique tasks, files changed, violations, drift signals); forge metrics without --json is unchanged.
Validation: 5 new tests pass (`TestFormatMetricsJson` + 2 CLI tests in `test_metrics.py`); full suite 317 tests pass. Runtime confirmed against this repo — `forge metrics --json` prints valid, parseable JSON matching the text report's values.
Risks or assumptions: Versioned the same way as `forge export` (a top-level `"version": "1"` field) — bump only on a removed field or changed meaning, not for additive fields.
Notes: Deferred twice already (Roadmap v5 planning, tabled pending a dashboard decision). Decided in Roadmap v6 planning to build it now regardless of whether a dashboard materializes — useful for scripting either way.

### AUTO-046 — Document a CI recipe for forge check
Priority: P2
Status: DONE

Goal: Document a CI pipeline recipe (Forgejo Actions and/or GitHub Actions) that runs forge check on every PR, so drift/lint/policy violations are caught before merge, not only locally via forge watch.
Why it matters: forge watch only catches regressions if someone remembers to run it locally between sessions. A CI gate catches them on every push/PR automatically, with no reliance on memory.
Scope: Documentation only — a worked example workflow YAML plus a docs/CI.md explaining setup. Do not add an actual .forge/workflows file to this repo unless explicitly requested; keep it a documented recipe others can adopt.
Expected files or areas: docs/CI.md, README.md
Acceptance criteria: docs/CI.md includes a complete, copy-pasteable workflow YAML that installs the package and runs forge check with a non-zero exit failing the job; README links to it.
Validation: Documentation-only change; full suite unaffected (317 tests pass, no code touched). Verified at runtime that `forge check` correctly self-resolves its validation command from `.forge/policy.md`'s Validation expectations section without any external PYTHONPATH set — confirming the recipe's claim that no `--cmd` override is normally needed.
Risks or assumptions: The workflow YAML targets `ubuntu-latest` and Python 3.12 as a reasonable default; adopters should adjust to their own runner/version needs. Not tested against a live Forgejo Actions or GitHub Actions runner — the YAML follows documented, standard syntax for both, but wasn't executed end-to-end on a real CI runner as part of this task.
Notes: Deferred twice already (Roadmap v5 planning). Decided in Roadmap v6 planning to document it now regardless of dashboard status, since it's independently useful.

### AUTO-047 — Add forge revert to undo a completed task's commit
Priority: P2
Status: DONE

Goal: Add forge revert <AUTO-###> that cleanly undoes a task's commit (via git revert) and flips its plan status back to TODO, for when a DONE task turns out to be wrong.
Why it matters: Nothing previously closed this loop — undoing a bad DONE task required manual `git revert` plus a manual `forge mark ... TODO`, with no single command tying the two together.
Scope: Look up the task's commit hash (from forge log/run history or a --commit override), run git revert on it, and call the existing mark logic to flip Status back to TODO. Does not touch Forgejo directly — a subsequent forge sync will reopen the issue naturally since the plan is the source of truth.
Expected files or areas: src/autonomous_forge/revert.py, src/autonomous_forge/cli.py, tests, docs/COMMANDS.md
Acceptance criteria: forge revert AUTO-### runs git revert on the task's recorded commit, flips the task's Status back to TODO, and reports the new revert commit hash; fails clearly if no commit hash can be found for the task or if git revert conflicts.
Validation: 12 new tests pass (`test_revert.py`, real-git integration including a genuine conflicting-revert case); full suite 329 tests pass. Runtime confirmed in a throwaway clone of this actual repo against two real commits: a conflicting revert (aborted cleanly, working tree untouched, plan Status unchanged) and a clean revert (succeeded, created a real revert commit, correctly detected the target commit's diff had already included the Status line and reported "Already TODO" instead of double-flipping).
Risks or assumptions: Commit lookup matches on the run-history `Task:` field's prefix, same convention as elsewhere in this codebase (e.g. `format_run_outcome`'s "Task: <id> — <title>" line) — a task with no recorded commit (e.g. `--no-save` was used, or history was pruned) requires `--commit` explicitly. A conflicting revert always aborts automatically rather than leaving a half-finished state for the human to resolve — intentionally conservative, matching the project's stated non-goal of automatic conflict resolution (see AUTO-033's push-conflict handling for the same precedent).
Notes: Closes a real gap: nothing currently undoes a completed task cleanly short of manual git surgery plus a manual forge mark. Originally scoped for Roadmap v5, deferred to v6 to keep v5 to its four core reliability tasks. Completes Roadmap v6 (AUTO-043 through AUTO-047, all DONE).

## Roadmap v7

### AUTO-048 — Make policy fail-closed on missing/malformed policy
Priority: P0
Status: DONE

Goal: Missing or malformed .forge/policy.md should block commit, pipeline --commit, mark, plan add, and import-orphans by default, instead of silently skipping diff-check as it does today.
Why it matters: A tool whose safety narrative depends on a policy file being enforced must not silently downgrade to "no enforcement" the moment that file goes missing or breaks — that gap made the allowlist/prohibited-paths guarantee unreliable exactly when it mattered most.
Scope: commit.py currently does 'if policy_text: check_diff_against_policy(...)' — when policy_text is None/malformed, no check runs and the commit can proceed. Change the default to block in that case, with a clear message. Add an explicit, prominently named override flag (e.g. --no-policy-required) for repos that intentionally have no policy yet (matches forge init's own bootstrap window).
Expected files or areas: src/autonomous_forge/commit.py, src/autonomous_forge/run.py, src/autonomous_forge/cli.py, tests, docs/COMMANDS.md, .forge/policy.md
Acceptance criteria: A repo with no .forge/policy.md fails forge commit/forge pipeline --commit by default with a clear message; the override flag restores today's behavior explicitly; a malformed policy also blocks by default.
Validation: `python -m pytest` — 343 tests pass (13 new: test_policy.py x3, test_commit.py x4, test_run.py x3, test_pipeline.py x2, plus one CLI override case). `forge lint-plan` — ok.
Risks or assumptions: Narrowed scope during implementation — `mark`, `plan add`, and `import-orphans` never performed diff-checking against arbitrary changed files (they only ever wrote to `.ai/AUTONOMOUS_PLAN.md`, an always-allowed path), so there was no existing fail-open gap there to close. Added `require_policy` (default True) with a `--no-policy-required` override only to `run`/`commit`/`pipeline`, the commands that actually perform diff-checking today. Extending policy gating to plan-mutation commands would be new functionality, not a fix to the documented gap — left for a separate decision if wanted.
Notes: See DEC-012. Independently verified: commit.py's diff-check is entirely skipped (not just relaxed) when policy_text is falsy — this is a real fail-open gap, not a documentation quibble. New `autonomous_forge.policy.validate_policy_text()` helper centralizes the missing/malformed check; block messages point users at `--no-policy-required`. docs/POLICY.md's "Conservative defaults" section rewritten from aspirational language to describe actual enforcement.

### AUTO-049 — Enforce the allowlist - not-allowed violations block by default
Priority: P0
Status: DONE

Goal: Files outside .forge/policy.md's Allowed paths should block forge run/forge commit by default, not just get reported - currently only rule == 'prohibited' violations block; 'not-allowed' violations are collected but never stop anything.
Why it matters: An allowlist that only warns is not a boundary — the same class of gap as AUTO-048's missing-policy hole, but for the common case where a policy exists and is well-formed but a change simply falls outside it.
Scope: run.py and commit.py both filter to only the 'prohibited' rule and only block on that list. Change the default blocking set to include 'not-allowed' too. Add an explicit opt-out (e.g. --advisory-paths or a policy-level flag) for repos that want the old warn-only allowlist behavior.
Expected files or areas: src/autonomous_forge/run.py, src/autonomous_forge/commit.py, src/autonomous_forge/cli.py, tests, docs/COMMANDS.md
Acceptance criteria: A changed file outside Allowed paths blocks forge run/forge commit by default with a clear message distinguishing it from a prohibited-path block; the opt-out restores today's advisory-only behavior explicitly.
Validation: `python -m pytest` — 351 tests pass (8 new: test_run.py x2, test_commit.py x4, test_pipeline.py x2). `forge lint-plan` — ok.
Risks or assumptions: None — this repo's own .forge/policy.md already covers every path this session has touched (src/**, tests/**, docs/**, .ai/**), so turning on default blocking here caused no friction.
Notes: See DEC-012. This exact gap was hit directly this session - .forge/config.toml and .gitignore showed not-allowed warnings on every commit (AUTO-039, AUTO-040) until the allowlist was manually widened (DEC-011), because nothing actually enforced the boundary. Added `advisory_paths` (default False) to run_pre_flight/execute_commit/execute_run/execute_pipeline, with a `--advisory-paths` CLI override on run/commit/pipeline mirroring AUTO-048's `--no-policy-required` pattern. Prohibited-path blocking is checked first and is never overridable by --advisory-paths — only the not-allowed (outside-allowlist) case is affected.

### AUTO-050 — Define structured approval semantics for policy's Human approval required section
Priority: P1
Status: DONE

Goal: Replace the prose-only 'Human approval required' policy section with a structured mechanism that actually gates matching actions, instead of being surfaced only in context/reporting with no enforcement.
Why it matters: A policy section that lists approval-required categories but is only ever displayed, never enforced, gives a false sense of safety — identical in kind to the two gaps DEC-012 already fixed, just for behavioral categories instead of file paths.
Scope: Design question, not just implementation - needs a decision on mechanism (an approved-task-ID list, a recorded approval note referenced by forge commit, or a required interactive confirmation scoped to the matching category) before building. Should integrate with the fail-closed changes in this same roadmap rather than being a third, inconsistent enforcement path.
Expected files or areas: src/autonomous_forge/plan.py, src/autonomous_forge/approvals.py (new), src/autonomous_forge/commit.py, src/autonomous_forge/run.py, src/autonomous_forge/cli.py, tests, docs/COMMANDS.md, docs/POLICY.md
Acceptance criteria: A task whose plan entry sets `Approval needed: <category>` blocks `forge run`/`forge commit`/`forge pipeline` by default until `forge approve <task-id> "<category>"` records a matching entry in `.forge/approvals.md`; the exact mechanism was decided and confirmed with the user (DEC-013) before implementation began.
Validation: `python -m pytest` — 367 tests pass (16 new: test_plan.py x1, test_approvals.py x9 in a new file, test_commit.py x3, test_run.py x2, plus one CLI end-to-end case). `forge lint-plan` — ok. Manually smoke-tested the full flow (blocked -> forge approve -> unblocked) in a scratch repo.
Risks or assumptions: Deviated from the acceptance criteria's original "detected against the actual diff" framing — confirmed with the user that automatic diff/content detection was rejected as too heuristic (see DEC-013 alternatives); detection is self-declared via the plan's `Approval needed:` field instead, not diff-derived. A task author who omits the field gets no gate — an accepted limitation, not an oversight, matching the trust model already extended to every other self-reported plan field.
Notes: The biggest open design question in Roadmap v7 - do not silently pick a mechanism; confirm with the user first, same as DEC-010's Forgejo-import design discussion. See DEC-013 for the full design record, including alternatives considered (automatic keyword matching, interactive-only confirmation, descoping entirely) and why each was rejected.

### AUTO-051 — Replace shell=True in forge validate with safer execution
Priority: P1
Status: DONE

Goal: validate.py runs the validation command via subprocess.run(..., shell=True); replace with array-based execution where possible, or require an explicit opt-in flag for shell-interpreted commands.
Why it matters: shell=True on a command sourced from file content (.forge/policy.md's Validation expectations prose) means an unreviewed or malicious policy edit could inject shell syntax; unconditional shell=True made this the default posture even for the common case that never needed it.
Scope: Split validation commands into two paths: simple space-separated commands run as an argv list (no shell), commands needing real shell features (pipes, &&, env expansion) require an explicit --allow-shell-command flag. The command can come from a CLI flag or from policy Markdown prose (.forge/policy.md's Validation expectations section) - the policy-sourced path is the more concerning one since it's file content, not a direct CLI argument.
Expected files or areas: src/autonomous_forge/validate.py, src/autonomous_forge/cli.py, tests, docs/COMMANDS.md
Acceptance criteria: A default validation command (e.g. python -m pytest) runs without shell=True; a command needing shell features fails clearly without --allow-shell-command and succeeds with it; existing default behavior for the common case is unaffected.
Validation: `python -m pytest` — 379 tests pass (12 new: test_validate.py, including a quote-aware `_needs_shell` unit-test class). `forge lint-plan` — ok.
Risks or assumptions: `_needs_shell()` is a simple quote-aware character scanner, not a full shell grammar parser — it does not handle backslash-escaped quotes. Fixed one real bug found while testing: a naive (non-quote-aware) first draft misclassified `python -c "import time; time.sleep(1)"` as needing shell, because it saw the semicolon inside the quoted Python one-liner; the scanner now tracks single/double-quote state and ignores metacharacters inside quotes.
Notes: Independently verified: validate.py's subprocess.run call does pass shell=True today. Lower urgency for a personal/trusted repo, but real for shared repos or unreviewed policy edits. Also added a `forge validate` docs/COMMANDS.md section — the command existed but was previously undocumented.

### AUTO-052 — Make .forge/.lock acquisition atomic
Priority: P1
Status: DONE

Goal: Replace the check-then-write lock acquisition in lock.py (path.exists() then write_text()) with an atomic exclusive-create primitive, closing the TOCTOU race where two processes can both observe no lock and both create one.
Why it matters: The entire point of the lock is preventing two concurrent forge run/pipeline invocations from double-committing; a check-then-write race meant the guarantee could silently fail under real concurrency, exactly the scenario it exists to prevent.
Scope: Use O_CREAT | O_EXCL (or the platform-appropriate atomic equivalent) to acquire the lock file, so a second concurrent acquire attempt fails atomically instead of racing. Keep the existing stale-lock detection and recovery (dead PID clears automatically) - only the acquisition step itself needs to become atomic.
Expected files or areas: src/autonomous_forge/lock.py, tests
Acceptance criteria: A tight-loop concurrent-acquire test (two near-simultaneous acquire attempts) never succeeds twice; existing stale-lock and release behavior from AUTO-040 is unaffected.
Validation: `python -m pytest` — 380 tests pass (1 new: a thread-based concurrent-acquire test using distinct faked pids per thread, since two threads share the same real os.getpid()). Ran the new concurrency test 5x standalone with no flakes. `forge lint-plan` — ok.
Risks or assumptions: The bounded retry loop (3 attempts) assumes at most a handful of processes ever race for this lock in practice (a personal/small-team tool) — if all attempts are exhausted by real contention it raises LockHeldError using whatever pid is currently recorded, which is the same outcome a caller would want (back off and retry later).
Notes: Independently verified: lock.py's acquire_lock does 'if path.exists(): ...' then 'path.write_text(...)' with no atomicity between the check and the write - a real TOCTOU gap, not just a theoretical one. Fixed with os.open(path, O_CREAT | O_EXCL | O_WRONLY), which is atomic at the OS level on both POSIX and Windows.

### AUTO-053 — Require forge lint-plan to pass before mutable pipeline stages
Priority: P2
Status: DONE

Goal: A malformed plan should never be used to select, commit against, or sync tasks - currently forge run/forge commit/forge pipeline proceed on a plan with lint failures, since normal execution never requires forge lint-plan to pass first.
Why it matters: Selecting or committing against a structurally malformed plan (duplicate IDs, unsupported priority/status, missing required fields) can silently pick the wrong task or corrupt plan state further — the same fail-closed logic already applied to file policy in DEC-012/013 applies equally to plan structure.
Scope: Run the existing lint_plan_structure check as a pre-flight gate inside execute_run/execute_commit (or pipeline's own entry point) before task selection, with a clear block message and the same override-flag pattern as the policy fail-closed task.
Expected files or areas: src/autonomous_forge/run.py, src/autonomous_forge/commit.py, src/autonomous_forge/pipeline.py, src/autonomous_forge/cli.py, tests, docs/COMMANDS.md
Acceptance criteria: A plan with a lint diagnostic (e.g. missing required field) blocks forge run/forge pipeline by default with the lint detail included; a clean plan is unaffected; the override flag restores today's behavior.
Validation: `python -m pytest` — 388 tests pass (8 new: test_run.py x2, test_commit.py x4, test_pipeline.py x2). `forge lint-plan` — ok. Confirmed `forge run --dry-run` still works correctly against this repo's real plan.
Risks or assumptions: This gate broke 26 previously-passing tests across test_run.py/test_pipeline.py/test_commit.py whose shared plan fixtures (MINIMAL_PLAN, PLAN_TODO, PLAN_WITH_TODO, etc.) only ever set Priority/Status/Goal — never the full 10-field set lint_plan_structure requires. Fixed by adding a shared _LINT_CLEAN_TAIL fixture block (Why it matters/Scope/Expected files or areas/Acceptance criteria/Validation/Risks or assumptions/Notes) to all 8 named plan fixtures across those three files, rather than special-casing require_lint_pass=False per test — those fixtures represent "a valid plan" for tests not about lint itself, and should now actually be valid under the new default.
Notes: Complements the policy fail-closed tasks - same fail-closed philosophy applied to plan structure instead of file policy. New CLI flag: --no-lint-required, mirroring --no-policy-required's naming pattern.

### AUTO-054 — Split cli.py and sync.py into smaller modules
Priority: P3
Status: DONE

Goal: cli.py (~1300 lines) and sync.py (~700 lines) have grown into monoliths mixing dispatch/orchestration with business logic; split them into smaller, clearer modules before more commands are added.
Why it matters: A single long if/elif dispatch chain and a file mixing HTTP transport with reconciliation logic and orphan-import logic both make it easy for a new command or feature to accidentally duplicate or diverge from existing patterns, and hard to unit-test one concern (e.g. label reconciliation) without dragging in the others.
Scope: cli.py: keep argument parsing thin, move each command's dispatch handler into its own function or module rather than one long if/elif chain in main(). sync.py: separate the Forgejo HTTP transport (ForgejoClient) from issue-matching/label/milestone reconciliation logic and from the orphan-import logic, which are currently all in one file.
Expected files or areas: src/autonomous_forge/cli.py, src/autonomous_forge/sync.py, tests
Acceptance criteria: No behavior change - same commands, same output, same exit codes. cli.py's main() dispatch chain and sync.py's responsibilities are demonstrably split into smaller, independently testable units. Full test suite passes unchanged.
Validation: `python -m pytest` — 388 tests pass, same count as before this task (pure internal reorganization, no new test scenarios added — existing tests moved and had patch targets updated to match new module boundaries). `forge lint-plan` — ok. Manually verified `forge plan` (no subcommand), `forge lint-plan`, and `forge status` all still work.
Risks or assumptions: Found and fixed a genuine pre-existing bug while touching this code: `forge plan` with no subcommand crashed with `NameError: name 'plan_parser' is not defined` — `plan_parser` was a local variable inside `build_parser()`, never actually in scope inside `main()`'s dispatch block. Replaced with the top-level `parser.print_help()` (general help instead of plan-specific help, but no longer crashes). Untested edge case, so it went unnoticed until this refactor.
Notes: Structural refactor only - explicitly no behavior changes (aside from the incidental bugfix above), to keep this reviewable as pure internal reorganization separate from the safety-semantics changes elsewhere in this roadmap. Final split: cli.py's main() is now a thin dispatch-table lookup over 29 independent `_cmd_*` handler functions (each independently callable/testable) instead of a 344-line if/elif chain. sync.py (692 lines) split three ways: forgejo_client.py (new, ~125 lines — ForgejoClient + repo/token detection, no plan.py dependency), sync.py (365 lines — SyncAction/SyncResult/execute_sync + issue-matching/label/milestone reconciliation), sync_orphans.py (new, ~219 lines — OrphanReport/ImportResult + execute_orphan_report/execute_import_orphans). Test files mirrored the split: test_forgejo_client.py (new), test_sync.py (trimmed), test_sync_orphans.py (new) — patch targets updated from `autonomous_forge.sync.X` to `autonomous_forge.sync_orphans.X`/`autonomous_forge.forgejo_client.X` wherever the patched call site actually moved modules.

### AUTO-055 — Add real CI enforcement to this repo (not just documented)
Priority: P2
Status: DONE

Goal: docs/CI.md documents a CI recipe but this repo doesn't run it on itself. Add an actual Forgejo Actions workflow here, plus basic dev-quality tooling (linter, type checker, coverage) that pyproject.toml currently has none of.
Why it matters: A documented-but-unenforced CI recipe is exactly the kind of gap that erodes trust in a tool whose purpose is enforcing checks — "we recommend this" is not the same guarantee as "this repo runs it on every push."
Scope: Add .forgejo/workflows/forge-check.yml following docs/CI.md's documented recipe. Add Ruff (lint) and a type checker (mypy or pyright) as dev-only tooling in pyproject.toml's optional-dependencies (not runtime deps - keep the zero-runtime-dependency guarantee intact). Wire both into the CI workflow alongside forge check and pytest.
Expected files or areas: .forgejo/workflows/forge-check.yml, pyproject.toml, docs/CI.md, README.md
Acceptance criteria: A pushed commit triggers the Forgejo Actions workflow and runs forge check plus the test suite; pyproject.toml declares dev extras for lint/type-check tooling; docs/CI.md is updated to note this repo now dogfoods its own documented recipe.
Validation: `python -m pytest` — 401 tests pass. `ruff check .` and `mypy` both report zero issues (see Risks). `forge lint-plan` — ok. `forge drift` — clean. Checked the Forgejo Actions API after pushing (`GET /repos/frank/Autonomous_Forge/actions/tasks`) — the repo reports `has_actions: true`, but `workflow_runs` was empty (0 runs) after the push that added the workflow file, meaning no runner actually picked up the job. Confirmed with the user this is acceptable to leave as-is for now (runner attachment treated as a separate infra task outside this repo's scope) — the acceptance criteria's "a pushed commit triggers the workflow" is therefore NOT independently verified end-to-end, only that the workflow file, dev tooling, and policy changes are correctly in place.
Risks or assumptions: Ruff's true out-of-the-box defaults (not this repo's config) surfaced 93 findings across plugin rule sets (bandit, pylint, flake8-simplify, etc.) never adopted here — deliberately scoped `[tool.ruff.lint]` down to `E4/E7/E9/F/I` (pyflakes + core pycodestyle + import sorting) so CI starts green rather than red on day one; adopting the broader rule set is a separate future decision, not silently bundled into this task. mypy surfaced 9 real findings (loose `_request` return typing in the new forgejo_client.py, one variable redefinition in sync.py) — fixed with `typing.cast()` at each call site and a rename, not suppressed. `.forgejo/workflows/**` was not in `.forge/policy.md`'s Allowed paths — added it, since AUTO-049 made the allowlist fail-closed and this repo needs to be able to maintain its own CI file through normal commits. Did not wire pytest-cov into a blocking coverage threshold in CI — an arbitrary percentage gate with no baseline data to justify it would be a separate, deliberate decision. Most significant open risk: no confirmed runner is attached, so the workflow may silently never execute until infra is fixed — worth a `forge doctor` extension or a follow-up task to actually confirm a green run once a runner exists.
Notes: Confirmed with the user that Forgejo Actions is available on forgejo.familytechlab.com before implementing (was on hold; user said "go ahead"). docs/CI.md and README.md both updated to describe the dev extras and the two new CI steps. After pushing, discovered and reported to the user that no workflow run was actually recorded (likely no runner attached) — user chose to accept the task as done and treat runner setup as separate infra work.

### AUTO-056 — Handle the AUTO-999 task ID ceiling
Priority: P3
Status: DONE

Goal: Task heading regex is fixed to exactly 3 digits, hard-capping IDs at AUTO-999. Currently at AUTO-047 with plenty of headroom, but the ceiling should be handled deliberately rather than discovered as a production failure.
Why it matters: A fixed-3-digit heading regex doesn't error loudly at AUTO-1000 — it just silently fails to match the whole heading line, so the task disappears from parsing entirely (not selected, not lint-checked, not synced) with no error message pointing at why.
Scope: Either widen the regex to allow 3+ digit IDs going forward (zero-padded to at least 3, no upper bound) or explicitly document and test a migration path for when the ceiling is approached. Prefer widening the regex - simpler, backward compatible with all existing 3-digit IDs, no migration needed.
Expected files or areas: src/autonomous_forge/plan.py, src/autonomous_forge/planadd.py, tests
Acceptance criteria: forge plan add correctly generates AUTO-1000 after AUTO-999 exists (tested with a synthetic high-numbered fixture, not by actually creating 999 real tasks); all existing 3-digit task IDs continue to parse and sort correctly.
Validation: `python -m pytest` — 394 tests pass (6 new: test_planadd.py x2, test_plan.py x2, test_drift.py x2). `forge lint-plan` — ok.
Risks or assumptions: `planadd.py`'s `f"AUTO-{next_num:03d}"` ID-generation format already worked correctly beyond 999 with no change needed (Python's `:03d` is a minimum width, not a truncation) — the ceiling bug was entirely in parsing regexes, not generation.
Notes: Low urgency at 47/999 tasks used, but cheap to fix now versus rediscovering it as a production bug at scale. Widened `\d{3}` to `\d{3,}` in four places beyond plan.py's main task-heading regex, found by grepping the whole codebase for the same fixed-width pattern: `approvals.py`'s approval-heading regex, and three regexes in `drift.py` (changelog task-heading match, state-file current-task-ID match, changelog-vs-plan task-ID validity check) — all four would have hit the identical silent-non-match failure mode at AUTO-1000 if left unfixed alongside the main one.

### AUTO-057 — Fix README's stale roadmap/test-count stats and add a drift check for them
Priority: P1
Status: DONE

Goal: README currently says Roadmap v1-v4 complete (37/37 tasks, 253 tests) - actual state is v6 complete (47/47 tasks, 329 tests). Fix it now, and add a check that catches this class of staleness automatically going forward.
Why it matters: A tool whose entire purpose is catching metadata drift having its own README silently drift out of date is the most self-undermining possible instance of the problem it exists to solve.
Scope: Update README.md's status line to current, accurate numbers. Then extend forge drift (or forge check) to flag when README's stated task/test counts diverge from the actual plan file's DONE count and the last recorded test count in AUTONOMOUS_STATE.md, so this can't silently drift again.
Expected files or areas: README.md, src/autonomous_forge/drift.py, tests, docs/COMMANDS.md
Acceptance criteria: README's status line matches current reality; forge drift reports a signal when README's stated counts no longer match the plan file's DONE count or the state file's last test count.
Validation: `python -m pytest` — 400 tests pass (6 new: test_drift.py x5, test_check.py x1). `forge lint-plan` — ok. `forge drift` against this repo's real files (after this task's own DONE flip and state update) reports no drift.
Risks or assumptions: The check requires README's status line to use an exact phrasing — `(N/M tasks done)` and `(N tests passing)` — and the state file's test count to appear as `<N> tests pass` right after "Validation commands and results:". If either format changes without updating the regex, the check silently does nothing rather than false-flagging — matches this project's general "prefer false negatives over unsafe/wrong assertions" posture (see docs/POLICY.md's now-corrected "Conservative defaults" language from DEC-012/013, same philosophy applied here).
Notes: Flagged by the assessment as especially damaging given the project's whole purpose is preventing exactly this kind of metadata drift. Quick fix for the immediate staleness; the drift-check extension prevents recurrence. New signal categories: `readme-plan`, `readme-state` (both `warn` severity — surfaced by both `forge drift` and `forge check`, never blocking since README staleness isn't a safety issue the way a missing policy or unapproved change is).

## Roadmap v8

Sourced from `docs/SECURITY_ASSESSMENT_2026-08-23.md` (2026-08-23 external security/completeness assessment). Grouped by dependency: fail-closed correctness bugs first, then policy-ordering fixes, then documentation/positioning, then robustness/hardening. See DEC-015 in `.ai/DECISIONS.md` for the grouping rationale.

### AUTO-058 — Fix forge check's fail-open policy-diff exception handling
Priority: P1
Status: DONE

Goal: `execute_check` (`src/autonomous_forge/check.py:89-98`) only runs the diff policy check if a policy file exists, then wraps it in a bare `except Exception:` that silently leaves `diff_ok=True`. A missing, unreadable, malformed, or internally failing policy check currently reports PASS.
Why it matters: `forge check` is the advertised all-in-one verification command and the intended CI signal. A tool whose purpose is trustworthy gating must not report success when the gate didn't actually run — this directly contradicts README's "forge check enforces policy" claim (SEC-003 in the assessment).
Scope: Narrow the exception handling to specific expected exception types; any other failure (including missing/malformed policy) must set `diff_ok=False` and surface the error in output, not swallow it silently.
Expected files or areas: src/autonomous_forge/check.py, tests
Acceptance criteria: `forge check` fails when the policy file is missing, malformed, unreadable, or the diff-policy checker raises unexpectedly. New regression tests cover all four cases.
Validation: `python -m pytest` — 411 tests pass (5 new: missing-policy-fails-closed, missing-policy-override, malformed-policy-fails-closed, unreadable-policy-fails-closed, unexpected-exception-not-swallowed). `ruff check .` — clean. `mypy` — clean. `forge lint-plan` — ok. Manually verified against a throwaway repo: malformed policy → exit 1 with a clear message; missing policy → exit 1 by default, exit 0 with `--no-policy-required`.
Risks or assumptions: Resolved the open "no policy at all" question by matching `commit.py`/`run.py`'s existing `require_policy` pattern exactly — missing policy now fails closed by default too, with the same `require_policy=False` / `--no-policy-required` escape hatch those commands already use, for consistency across all three gating commands. Also fixed an adjacent bug found while testing: the Drift block's own `policy.read_text()` call (line 69) only caught `(FileNotFoundError, PlanParseError)`, so an unreadable (not just missing) policy file crashed `forge check` entirely before ever reaching the diff-check block — widened to `(OSError, PlanParseError)`; Drift stays advisory/non-blocking either way (unchanged from AUTO-057's design), only the diff-check gate is newly blocking.
Notes: Assessment reference: SEC-003. Added `--no-policy-required` to both `forge check` and `forge watch` (which wraps `execute_check`) for symmetry with `forge run`/`forge commit`/`forge pipeline`'s existing flag. docs/COMMANDS.md updated with the new flag and a fail-closed example for both commands.

### AUTO-059 — Return exit code 1 when pipeline sync fails
Priority: P1
Status: DONE

Goal: `execute_pipeline` records sync errors in `stopped_reason` (`src/autonomous_forge/pipeline.py:222-235`), but `_cmd_pipeline` (`src/autonomous_forge/cli.py:1262-1269`) only checks run/commit/push failures before returning 0. The documented exit-code contract promises exit 1 for sync errors.
Why it matters: A CI script or wrapper relying on `forge pipeline`'s exit code to detect failure will see success even when Forgejo sync errored.
Scope: Check `sync_result.errors` in `_cmd_pipeline` and return 1 when nonempty, matching the same pattern already used for run/commit/push.
Expected files or areas: src/autonomous_forge/cli.py, tests
Acceptance criteria: A CLI-level test simulates a sync error and asserts exit code 1.
Validation: `python -m pytest` — 412 tests pass (1 new: `test_pipeline_sync_errors_exit_1`, a CLI-level test that patches `execute_pipeline` to return a `PipelineResult` with `sync_result.errors` set and asserts `main()` returns 1). `ruff check .` — clean. `mypy` — clean. `forge lint-plan` — ok. Manually verified: invoking `main()` with a mocked sync-error result prints "Stopped: Sync errors: ..." and returns exit code 1.
Risks or assumptions: None significant — small, isolated fix; three-line change in `_cmd_pipeline`.
Notes: Assessment reference: COMP-003.

### AUTO-060 — Distinguish "no changes" from "could not inspect changes" in Git helpers
Priority: P2
Status: DONE

Goal: Several Git helpers, notably `get_changed_files` (`src/autonomous_forge/diffcheck.py:22-50`), return empty stdout without checking the subprocess return code, so a Git failure is indistinguishable from "no changes." In commit pre-flight this currently blocks (safe by accident), but in reports and `forge check` it can produce a false-clean signal.
Why it matters: Fail-open-by-accident is fragile — it happens to be safe today only because of how the result is currently consumed downstream; any future caller that doesn't share that assumption inherits a silent bug (SEC-008).
Scope: Audit `diffcheck.py` and any other Git helper with the same shape (grep for return-code-ignoring subprocess calls, similar to how AUTO-056 grepped for the fixed-width ID regex). Make Git failures raise or return an explicit error/result type distinct from "zero changed files." Fail closed anywhere the result gates a mutation or CI success.
Expected files or areas: src/autonomous_forge/diffcheck.py, other modules found by the audit, tests
Acceptance criteria: A simulated Git failure (e.g. not a repo, git binary missing) is distinguishable from a clean working tree in every caller that currently can't tell them apart, with tests for each.
Validation: `python -m pytest` — 417 tests pass (412 baseline + 5 new: `get_changed_files` raises on git failure, `forge diff-check` reports "could not inspect changes" and exits 1 in a non-repo directory, `forge commit`/`forge run`/`forge check` each block/fail with a distinct "Could not determine changed files" message instead of the misleading "No changed files" or a silent PASS). `ruff check .` — clean. `mypy` — clean. `forge lint-plan` — ok. Manually verified against a real non-git directory: `forge diff-check` and `forge check` both report the specific git error and exit 1; `forge commit` blocks with the distinct message instead of "No changed files to commit."
Risks or assumptions: Audited every `subprocess.run`/`check_output`/`call` site in `src/autonomous_forge/*.py` (12 total). Found one more helper with the identical shape: `session.py`'s `_run_git` (used only by `forge pause`'s read-only git snapshot). Left it unchanged, deliberately — unlike `diffcheck.py`'s helper, nothing downstream treats its empty-on-failure result as a gating signal; it only affects what a human sees in a session handoff file, and `forge pause` already displays "unknown" for an unreadable branch. Revisit only if a future caller starts using it to gate a decision. `commit.py`'s own separate `_run_git` (used for `git add`/`git rev-parse` in the post-commit changelog-staging path) was also left untouched here — its return-code handling is explicitly AUTO-061's scope (SEC-005), not this task's, to avoid overlapping edits.
Notes: Assessment reference: SEC-008. Added `GitCommandError` (in `diffcheck.py`) as the shared signal for "git could not be run," raised by `_run_git`/`get_changed_files` and now handled explicitly by `check.py`, `commit.py`, `run.py`, and `read_diff_report`. Capped the exception message to git's first stderr line — the uncapped version was dumping git's full multi-page usage text (e.g. when `--cached` isn't a valid flag outside a repo) into every error report. Also added a `forge diff-check` section to docs/COMMANDS.md — it had no documentation at all before this task, a pre-existing gap unrelated to AUTO-060 but touched directly by its new exit-code behavior.

### AUTO-061 — Move changelog staging before the final commit policy check
Priority: P2
Status: TODO

Goal: `execute_commit` (`src/autonomous_forge/commit.py:125-296`) runs pre-flight policy checks against the currently staged files, then *afterward* generates and stages `.ai/AUTONOMOUS_CHANGELOG.md` and commits it — without re-running policy or validation against the now-different staged tree.
Why it matters: A repository whose policy disallows changes to the changelog path (or anywhere else the changelog-generation step happens to touch) can still have it committed, because the check ran against a staged tree that no longer matches what's actually committed (SEC-005).
Scope: Reorder `execute_commit` so changelog generation and staging happens before the final staged-diff policy check, so the check validates the exact tree that will be committed. Also check `git add`'s return code (currently unchecked).
Expected files or areas: src/autonomous_forge/commit.py, tests
Acceptance criteria: A policy that disallows the changelog path causes commit to fail closed even though changelog generation would otherwise have staged it. `git add` failure is detected and surfaced.
Validation: `python -m pytest`, `ruff check .`, `mypy`.
Risks or assumptions: Low risk, single-file change to control flow ordering.
Notes: Assessment reference: SEC-005.

### AUTO-062 — Verify staged changes match the selected task's declared scope
Priority: P2
Status: TODO

Goal: Nothing currently checks that the actually-staged diff corresponds to the selected task's Scope or Expected files. Unrelated staged changes can be committed under any task ID, and task selection can be influenced by an unstaged plan while the real commit contains something else (COMP-002).
Why it matters: This is the second half of "audit-integrity" alongside SEC-002's approval gate — a task ID in a commit message is currently a label, not a verified claim.
Scope: This is a design decision, not just a bugfix — resolve it via a short decision record before implementing (see DEC-015 note below). Candidate approach: compare the staged file set against the task's declared Expected files or areas immediately before commit; warn or block on mismatch depending on what the decision record settles on. Do not silently make this strict without discussing severity (warn vs. block) with the user first, since it changes commit UX for every existing workflow.
Expected files or areas: src/autonomous_forge/commit.py, src/autonomous_forge/plan.py, tests, .ai/DECISIONS.md
Acceptance criteria: TBD pending the decision record — at minimum, README/docs disclose plainly that task attribution is currently conventional, not verified, until this ships.
Validation: `python -m pytest`, `ruff check .`, `mypy`.
Risks or assumptions: Highest UX-impact task in this roadmap — get explicit sign-off on strictness (warn vs. hard block) before writing code, per this project's "ask, don't assume" default.
Notes: Assessment reference: COMP-002.

### AUTO-063 — Add SECURITY.md and a threat-model section to the README
Priority: P1
Status: TODO

Goal: `forge` executes repository-controlled validation code with the user's full privileges and environment (`src/autonomous_forge/validate.py:87-130`), and the "human approval required" mechanism is a self-declared, unauthenticated convention (`src/autonomous_forge/approvals.py:76-114`) — but the README doesn't state either limitation plainly (SEC-001, SEC-002).
Why it matters: These are acceptable, by-design tradeoffs for a trusted single-operator tool, but only if users know that's the model. Undisclosed, they read as safety claims the tool doesn't actually make.
Scope: Add a `SECURITY.md` at repo root covering: validation = full local code execution, not a sandbox; only run Forge against repositories/branches you trust; "human approval" = an auditable operator attestation, not authenticated approval. Add a short pointer/summary near the top of the README.
Expected files or areas: SECURITY.md (new), README.md
Acceptance criteria: Both documents plainly state the trust model before any usage instructions.
Validation: Manual read-through; `forge lint-plan`.
Risks or assumptions: Pure documentation — no code risk.
Notes: Assessment reference: SEC-001, SEC-002. Also closes part of COMP-005 (no SECURITY.md).

### AUTO-064 — Reframe README positioning away from "autonomous executor"
Priority: P1
Status: TODO

Goal: The roadmap already states the tool is "not ... an autonomous executor" (`.ai/AUTONOMOUS_PLAN.md:7-9` in the Product scope and non-goals section above), while the README currently calls it a tool for "autonomous software-improvement loops." The implementation selects a task, inspects the diff, runs validation, and optionally commits/pushes/syncs — it does not invoke an agent or apply a task itself (COMP-001).
Why it matters: Flagged by the assessment as the single biggest external-positioning risk — an easy "this isn't actually autonomous" rebuttal undermines everything else the tool does well.
Scope: Update README's framing to something like "workflow guardrails for human/agent-authored repository changes" — local-first planning, policy checks, validation, auditable run records, and opt-in commit/push/Forgejo sync. Explicitly not an agent runner.
Expected files or areas: README.md
Acceptance criteria: README and roadmap no longer contradict each other on what the tool does.
Validation: Manual read-through; `forge lint-plan`.
Risks or assumptions: Pure documentation — no code risk. Coordinate with AUTO-063 since both touch the README's opening section.
Notes: Assessment reference: COMP-001.

### AUTO-065 — Fix stale test-count and roadmap-count metadata across docs
Priority: P2
Status: TODO

Goal: README and `.ai/AUTONOMOUS_STATE.md` say 401 tests; actual is 406 as of this review. `.ai/AUTONOMOUS_PLAN.md`'s own "Current implementation status" section (line 17, above the roadmap table) still says "Roadmaps v1 through v6... 329 tests" despite the roadmap itself running through v7 (57/57) — a second, independent staleness this assessment surfaced. `docs/CODEBASE_ASSESSMENT.md` still presents 317 tests as current. `forge drift`'s README/state check (added in AUTO-057) compares two prose sources to each other, not to pytest's actual collected/passed count, so it didn't catch this drift (COMP-004).
Why it matters: The project's stated purpose is catching exactly this class of drift — every instance of it left uncorrected undermines the pitch.
Scope: Update the test/task counts in README.md, `.ai/AUTONOMOUS_STATE.md`, and `.ai/AUTONOMOUS_PLAN.md`'s "Current implementation status" paragraph to current, accurate numbers. Archive or clearly mark `docs/CODEBASE_ASSESSMENT.md` as historical. Extend `forge drift` (or a new signal) to derive the test count from an actual pytest run rather than comparing README prose against state-file prose.
Expected files or areas: README.md, .ai/AUTONOMOUS_STATE.md, .ai/AUTONOMOUS_PLAN.md, docs/CODEBASE_ASSESSMENT.md, src/autonomous_forge/drift.py, tests
Acceptance criteria: All four documents agree with each other and with a live `pytest -q` run; `forge drift` flags a machine-verified count instead of two hand-maintained numbers agreeing by coincidence.
Validation: `python -m pytest`, `forge drift` clean against the corrected files.
Risks or assumptions: Running pytest as part of `forge drift` adds real wall-clock cost to what's currently a fast static check — decide whether this belongs in `forge drift` itself or a separate opt-in `forge check --verify-counts` style flag.
Notes: Assessment reference: COMP-004.

### AUTO-066 — Redact secrets from persisted validation output
Priority: P3
Status: TODO

Goal: Validation captures stdout/stderr (`src/autonomous_forge/validate.py:122-137`), `execute_run` retains their tail (`src/autonomous_forge/run.py:301-318`), and run summaries write that output verbatim (`src/autonomous_forge/run.py:416-427`). The run directory is gitignored, but a test or tool that prints a token leaves it on disk, exposed to anyone with local file access or a copied diagnostic bundle (SEC-004).
Why it matters: Defense in depth for the one class of local risk this tool doesn't already gitignore-away.
Scope: Add best-effort redaction for common credential formats (API key prefixes, bearer tokens, etc.) and any configured secret values, before persisting validation output. Restrict run-file permissions where the platform supports it. Add an opt-in no-output-persistence mode.
Expected files or areas: src/autonomous_forge/validate.py, src/autonomous_forge/run.py, tests, README.md/SECURITY.md
Acceptance criteria: Known credential-shaped patterns are redacted in persisted run files; docs explicitly state this is best-effort, not complete secret detection.
Validation: `python -m pytest`, `ruff check .`, `mypy`.
Risks or assumptions: Must not overclaim — document as best-effort only, since arbitrary program output can leak secrets in unpredictable shapes no regex will catch.
Notes: Assessment reference: SEC-004.

### AUTO-067 — Make the Forgejo client configurable and harden its error handling
Priority: P3
Status: TODO

Goal: Repository detection and API URLs are hardcoded to `forgejo.familytechlab.com` (`src/autonomous_forge/forgejo_client.py:15-29`, `:55-75`), making the advertised Forgejo integration unusable for external adopters. The HTTP layer only catches `HTTPError`; DNS failures, refused connections, TLS failures, timeouts, malformed JSON, and unexpected response shapes can escape as raw tracebacks, since `sync.py` generally only catches `RuntimeError` (SEC-006).
Why it matters: Hardcoding one operator's own instance is fine for dogfooding but blocks anyone else from using `forge sync` at all — and unhandled transport errors surface as unfriendly stack traces instead of CLI errors.
Scope: Make the base URL configurable (repo config or env var, consistent with AUTO-039's config-defaults pattern). Validate it's HTTPS and well-formed. Normalize/validate owner and repo names. Catch `URLError`, timeout, JSON-decode, and unexpected-schema failures alongside `HTTPError`, returning consistent CLI-level errors.
Expected files or areas: src/autonomous_forge/forgejo_client.py, src/autonomous_forge/sync.py, src/autonomous_forge/config.py (if that's where AUTO-039's config lives), tests, docs/COMMANDS.md
Acceptance criteria: `forge sync` works against a configured non-default Forgejo instance in tests; simulated DNS/timeout/malformed-JSON failures produce a clean CLI error, not a traceback.
Validation: `python -m pytest`, `ruff check .`, `mypy`.
Risks or assumptions: Retry/backoff should only be added for idempotent reads, or with carefully scoped operation-specific semantics — do not blanket-retry mutating calls.
Notes: Assessment reference: SEC-006.

### AUTO-068 — Pin CI and dev-dependency supply chain
Priority: P3
Status: TODO

Goal: The build backend, dev tools, container image, OS packages, and `actions/checkout@v4` are all unpinned (`pyproject.toml:1-3`, `:25-32`; `.forgejo/workflows/forge-check.yml:9-22`), so a clean CI build can change without any repository change. Configured Ruff rules deliberately omit security rules — `ruff check src --select S` (run outside the normal CI config) surfaced 17 findings during this review, including the fail-open exception in check.py that's already AUTO-058 (SEC-007).
Why it matters: Reproducibility and supply-chain pinning are table stakes before calling CI "hardened" — right now a passing CI run today doesn't guarantee the same result tomorrow.
Scope: Pin `actions/checkout` by commit digest. Lock or pin dev dependencies (the `dev` extra added in AUTO-055). Pin the container image by digest for releases. Add a security-focused static-analysis CI job — decide whether that means enabling `S` in the existing scoped `[tool.ruff.lint]` selection or running it as a separate advisory job, since AUTO-055 deliberately scoped Ruff down to start CI green.
Expected files or areas: .forgejo/workflows/forge-check.yml, pyproject.toml, tests (if any pinning is testable)
Acceptance criteria: CI action and container references are pinned by digest; dev dependencies are locked; a security-rules CI job runs (even if advisory/non-blocking initially).
Validation: A pushed commit against the updated workflow; `ruff check .`.
Risks or assumptions: Adding `S` findings as blocking could reopen a large backlog similar to AUTO-055's original 93-finding out-of-the-box Ruff surface — start advisory/non-blocking, decide on enforcement separately.
Notes: Assessment reference: SEC-007. The one already-fixed-elsewhere finding from the `--select S` run (the check.py fail-open exception) is tracked as AUTO-058, not duplicated here.

### AUTO-069 — Alpha-readiness polish: coverage threshold, package metadata, compatibility matrix
Priority: P3
Status: TODO

Goal: No coverage threshold in CI, no project URLs in package metadata, and CI only runs Python 3.12 despite `pyproject.toml` claiming 3.10–3.12 support (COMP-005).
Why it matters: Minor individually, but each is a small credibility gap for anyone evaluating whether to adopt the tool.
Scope: Wire `pytest-cov` (already a dev extra from AUTO-055) into CI with a coverage report (threshold enforcement optional — decide based on current baseline, don't pick an arbitrary number). Add project URLs (repository, issues) to `pyproject.toml`. Add a CI matrix covering 3.10, 3.11, 3.12 to match the claimed support range, or narrow the claimed range to match what's actually tested.
Expected files or areas: pyproject.toml, .forgejo/workflows/forge-check.yml
Acceptance criteria: CI reports coverage; package metadata includes project URLs; claimed Python support range matches what CI actually exercises.
Validation: A pushed commit against the updated workflow; `python -m pytest --cov`.
Risks or assumptions: Lowest priority in this roadmap — pure polish, no behavior risk.
Notes: Assessment reference: COMP-005. `SECURITY.md` (also part of COMP-005) is covered by AUTO-063, not duplicated here.

## Future Ideas

- (empty — all previously listed ideas were promoted into Roadmap v4, v5, or v6)

## Do Not Change Without Explicit Human Approval

- Remote and branch settings.
- Repository visibility and access controls.
- Production infrastructure.
- Features that run external commands.
- Features that change repository files outside documented safe paths.
- Credential handling, telemetry, analytics, billing, or deployment behavior.
