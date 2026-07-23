# Autonomous Forge Roadmap

## Product vision

Autonomous Forge helps a repository keep a clear improvement plan, choose one small task, check the result, and record what happened.

## Product scope and non-goals

The first product remains a local Python command-line tool. It reads repository files, reports safe next actions, and keeps durable project memory. It is not a hosted platform, dashboard, autonomous executor, deployment system, or permission-management tool.

## Current architecture

The project has two interfaces: a Python CLI (`forge`) and Claude Code skills (`/pause`, `/resume`). The Python package lives under `src/autonomous_forge` with tests under `tests/`. See `docs/COMMANDS.md` for the full, current command reference (`forge --help` also lists every subcommand) — the roadmap task list above is the source of truth for what's been added. The Claude Code skills live in global config (`~/.claude/commands/`) and work in any repo. Session handoff files are stored in `.forge/sessions/` (gitignored). The project uses zero runtime dependencies; several commands shell out to `git`, and `forge sync` makes Forgejo API calls via stdlib `urllib`.

## Current implementation status

Roadmaps v1 through v4 are complete (37 tasks). Roadmap v4 added commit-hash-linked run reports, a read-only Forgejo orphan-issue report, cross-repo session handoff aggregation, and `forge watch`. All 251 tests pass at runtime.

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
Status: TODO

Goal: Add a `.forge/config.toml` (or similar) read by all commands, so repo-level defaults for --plan, --policy, --root, and --cmd stop needing to be passed on every invocation.
Why it matters: TBD
Scope: New optional config file, parsed once and merged with explicit CLI flags (explicit flags always win). forge init should scaffold a default config alongside existing templates.
Expected files or areas: src/autonomous_forge/config.py, src/autonomous_forge/cli.py, src/autonomous_forge/init.py, tests, docs/COMMANDS.md
Acceptance criteria: Commands use config-file values when a flag is omitted, explicit flags override config values, missing config file falls back to current hardcoded defaults with no behavior change.
Validation: TBD
Risks or assumptions: None.
Notes: Zero-dependency parsing preferred (stdlib tomllib on Python 3.11+, or a minimal conservative parser if broader Python support is required).

### AUTO-040 — Prevent concurrent forge run/pipeline collisions
Priority: P1
Status: TODO

Goal: Add a lightweight lock file so two concurrent `forge run`/`forge pipeline` invocations against the same repo cannot double-commit or race.
Why it matters: TBD
Scope: Acquire a .forge/.lock file (PID + timestamp) at the start of run/pipeline, release on exit (including on error), and fail fast with a clear message if a live lock is already held.
Expected files or areas: src/autonomous_forge/lock.py, src/autonomous_forge/run.py, src/autonomous_forge/pipeline.py, tests, docs/COMMANDS.md
Acceptance criteria: A second concurrent invocation fails fast with a clear 'already running (pid X)' message instead of racing; a stale lock (process no longer alive) is detected and cleared automatically; normal single-invocation runs are unaffected.
Validation: TBD
Risks or assumptions: None.
Notes: Guards against the realistic case of a human and an agent (or two agent sessions) running against the same repo at once — currently nothing prevents this.

### AUTO-041 — Auto-append completed tasks to the changelog
Priority: P2
Status: TODO

Goal: Have `forge commit`/`forge pipeline` append a line to .ai/AUTONOMOUS_CHANGELOG.md when a task's status flips to DONE, so the changelog stops silently drifting from the plan.
Why it matters: TBD
Scope: On successful commit of a task that is now DONE, append a dated one-line changelog entry (task ID, title, commit hash). Do not rewrite or reorder existing changelog content.
Expected files or areas: src/autonomous_forge/changelog.py, src/autonomous_forge/commit.py, src/autonomous_forge/pipeline.py, tests, docs/COMMANDS.md
Acceptance criteria: A completed task's commit appends exactly one new changelog line with task ID, title, and commit hash; non-DONE-flipping commits do not touch the changelog; existing changelog content is preserved verbatim.
Validation: TBD
Risks or assumptions: None.
Notes: The changelog file already exists in the metadata scaffold but nothing currently writes to it automatically — this closes that gap, mirroring how forge mark closes the manual-status-edit gap.

### AUTO-042 — Import orphan Forgejo issues into the plan as AUTO-xxx stubs
Priority: P2
Status: TODO

Goal: Add `forge sync --import-orphans` that converts current orphan Forgejo issues (from AUTO-035's --report-orphans) into new AUTO-xxx task stubs appended to the plan file, in one explicit, human-triggered run.
Why it matters: TBD
Scope: Reuse the existing orphan-issue detection from AUTO-035. For each orphan issue, append a new AUTO-xxx task block (title from issue title, Notes referencing the source issue number/URL, Status TODO, Priority P2 default) before Future Ideas, matching forge plan add's existing insertion behavior. No per-issue prompt; the human reviews the resulting plan diff before committing it. --report-orphans stays read-only and unchanged; --import-orphans is a separate, opt-in flag.
Expected files or areas: src/autonomous_forge/sync.py, src/autonomous_forge/planadd.py, src/autonomous_forge/cli.py, tests, docs/COMMANDS.md
Acceptance criteria: Running --import-orphans creates one AUTO-xxx stub per current orphan issue with correct auto-incremented IDs, each stub's Notes references the source Forgejo issue number; --report-orphans and plain --dry-run behavior are unaffected; re-running after a previous import does not duplicate stubs for issues already imported (idempotent against issues already referenced by an AUTO-xxx Notes field).
Validation: TBD
Risks or assumptions: None.
Notes: See DEC-010 in .ai/DECISIONS.md: this is an explicit, human-triggered partial reversal of AUTO-035's read-only-only stance — the human still reviews the plan diff before committing, preserving the plan as source of truth.

## Future Ideas

- (empty — all previously listed ideas were promoted into Roadmap v4)

## Do Not Change Without Explicit Human Approval

- Remote and branch settings.
- Repository visibility and access controls.
- Production infrastructure.
- Features that run external commands.
- Features that change repository files outside documented safe paths.
- Credential handling, telemetry, analytics, billing, or deployment behavior.
