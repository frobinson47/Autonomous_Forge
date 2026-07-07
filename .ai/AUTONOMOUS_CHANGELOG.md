# Autonomous Changelog

## 2026-07-07 — AUTO-021

- Task ID: AUTO-021
- Summary: Added `forge run` — the autonomous execution loop that ties task selection, validation, diff-check, drift detection, and run recording into a single command. Supports `--dry-run`, `--no-validate`, `--no-save`, and `--cmd` override. Blocked runs return exit code 1. Run outcomes persist to `.forge/runs/` (gitignored).
- Validation completed: 15 tests pass; full suite 96 tests pass. Runtime confirmed.
- Commit hash: pending
- Follow-up notes: This is the capstone command — the forge can now run a complete autonomous cycle. It does not auto-commit; that remains a human decision or future explicit opt-in.

## 2026-07-07 — AUTO-020

- Task ID: AUTO-020
- Summary: Added `forge validate` — runs the test suite or custom command, reports structured pass/fail. First forge command that executes external processes. Handles PYTHONPATH portably across platforms.
- Validation completed: 8 tests pass; full suite 81 tests pass. Runtime confirmed.
- Commit hash: 927cf15

## 2026-07-07 — AUTO-019

- Task ID: AUTO-019
- Summary: Added `forge diff-check` — validates changed files against policy allowed/prohibited paths. The safety gate before autonomous commits.
- Validation completed: 9 tests pass; full suite 81 tests pass. Runtime confirmed.
- Commit hash: 927cf15

## 2026-07-07 — AUTO-018

- Task ID: AUTO-018
- Summary: Added `forge init` — scaffolds `.ai/` and `.forge/` metadata into any repo. Creates plan, state, changelog, decisions, policy templates. Skips existing files.
- Validation completed: 6 tests pass; full suite 81 tests pass. Runtime confirmed.
- Commit hash: 927cf15

## 2026-07-07 — AUTO-017

- Task ID: AUTO-017
- Summary: Added `forge context` — composes task summary, state, policy, drift, and inventory into a one-screen briefing. Also created `/forge` Claude Code skill. Updated `docs/COMMANDS.md` with drift, pause, resume docs.
- Validation completed: 5 tests pass; full suite 81 tests pass. Runtime confirmed.
- Commit hash: 6cdd884

## 2026-07-07 — AUTO-016

- Task ID: AUTO-016
- Summary: Added `forge pause` and `forge resume` commands for session handoff — captures git state and mental context, serializes to Markdown, replays as a structured briefing. Also created universal Claude Code `/pause` and `/resume` skills that synthesize context from conversation history.
- Validation completed: 11 session tests pass; full suite 54 tests pass. Runtime test execution confirmed.
- Commit hash: fdde137
- Follow-up notes: The Claude Code skills are the primary interface. The Python CLI is the engine and fallback for non-Claude-Code environments.

## 2026-07-07 — AUTO-015

- Task ID: AUTO-015
- Summary: Added `forge drift` — a read-only metadata consistency detector that cross-checks plan, state, changelog, and policy files. Detects status mismatches, stale placeholders, phantom task references, and policy paths pointing at missing directories. Also installed pre-commit secret-leak guard.
- Validation completed: 13 drift tests pass; full suite 54 tests pass. Runtime test execution confirmed.
- Commit hash: 981d081
- Follow-up notes: First feature added by a human-AI pair. First time all tests were actually executed at runtime (previous 14 tasks only had static review).

## 2026-07-07 — AUTO-014

- Task ID: AUTO-014
- Summary: Added a read-only `forge inventory` command that reports deterministic present/missing file-presence signals for the documented repository health inventory scope.
- Validation completed: Static implementation review completed against AUTO-014 acceptance criteria; runtime test execution was unavailable in this automation environment.
- Commit hash: pending final commit lookup
- Follow-up notes: Reassess Roadmap v2 before adding any broader inspection or persistence behavior.

## 2026-07-07 — AUTO-013

- Task ID: AUTO-013
- Summary: Added `docs/HEALTH_INVENTORY.md` defining the safe first scope for a future read-only repository health inventory, including file-presence signals, output boundaries, and validation expectations.
- Validation completed: Static documentation review completed against AUTO-013 acceptance criteria; runtime test execution was unavailable in this automation environment.
- Commit hash: pending final commit lookup
- Follow-up notes: Implement a small read-only repository inventory command only if the documented scope remains acceptable.

## 2026-07-07 — AUTO-012

- Task ID: AUTO-012
- Summary: Added a read-only `forge run-summary` command that previews the documented local run-summary fields using the current plan and policy status, including placeholders for validation result, changed files, and commit.
- Validation completed: Static implementation review completed against AUTO-012 acceptance criteria; runtime test execution was unavailable in this automation environment.
- Commit hash: pending final commit lookup
- Follow-up notes: Reassess Roadmap v2 and add the next smallest read-only task before implementing further behavior.

## 2026-07-07 — AUTO-011

- Task ID: AUTO-011
- Summary: Added `docs/RUN_SUMMARIES.md` documenting the future local run-summary format, required fields, example preview, and safety limits that prevent automatic history-file writes until explicitly planned.
- Validation completed: Static documentation review completed against AUTO-011 acceptance criteria; runtime test execution was unavailable in this automation environment.
- Commit hash: pending final commit lookup
- Follow-up notes: Reassess Roadmap v2 and add the next smallest read-only task before implementing further behavior.

## 2026-07-07 — AUTO-010

- Task ID: AUTO-010
- Summary: Added `docs/COMMANDS.md` documenting implemented CLI command purposes, inputs, expected human-readable output patterns, exit-code expectations, and safety limitations; linked the command contracts from README.
- Validation completed: Static documentation review completed against AUTO-010 acceptance criteria; runtime test execution was unavailable in this automation environment.
- Commit hash: pending final commit lookup
- Follow-up notes: Proceed to AUTO-011 next so local run-summary format work can be designed without adding execution behavior.

## 2026-07-07 — AUTO-009

- Task ID: AUTO-009
- Summary: Added read-only roadmap structure linting through `forge lint-plan`, including required task fields, supported priority values, supported status values, CLI diagnostics, tests, and README usage notes.
- Validation completed: Static implementation review completed against AUTO-009 acceptance criteria; added unit and CLI coverage for valid plans, missing required fields, unsupported priorities, and unsupported statuses; runtime test execution was unavailable in this automation environment.
- Commit hash: pending final commit lookup
- Follow-up notes: Proceed to AUTO-010 next so command output contracts are documented after the new read-only command exists.

## 2026-07-07 — AUTO-008

- Task ID: AUTO-008
- Summary: Extended the read-only `forge report` output to include repository policy readiness as present/readable, missing, or malformed while avoiding any path enforcement claims.
- Validation completed: Static implementation review completed against AUTO-008 acceptance criteria; added CLI coverage for present, missing, and malformed policy states; runtime test execution was unavailable in this automation environment.
- Commit hash: pending final commit lookup
- Follow-up notes: Proceed to AUTO-009 next so roadmap structure can be linted before adding more commands.

## 2026-07-07 — AUTO-007

- Task ID: AUTO-007
- Summary: Added conservative read-only parsing for `.forge/policy.md`, exposed a `forge policy` summary command, documented the command, and added parser/CLI coverage for valid, missing, and malformed policy inputs.
- Validation completed: Static implementation review completed against the documented policy format; runtime test execution was unavailable in this automation environment.
- Commit hash: pending final commit lookup
- Follow-up notes: Proceed to AUTO-008 next so `forge report` can surface policy readiness without claiming enforcement.

## 2026-07-07 — Roadmap v2 planning

- Task ID: Roadmap v2 planning
- Summary: Added Roadmap v2 with conservative read-only tasks for policy parsing, policy readiness reporting, roadmap linting, command output documentation, and local run-summary planning.
- Validation completed: Static roadmap consistency review completed; runtime test execution was not available in this automation environment.
- Commit hash: pending final commit lookup
- Follow-up notes: Begin AUTO-007 next; do not implement later roadmap items during the same planning run.

## 2026-07-07 — AUTO-006

- Task ID: AUTO-006
- Summary: Added contributor development guidance for local setup, tests, task discipline, safe file handling, safety boundaries, and commit-message expectations.
- Validation completed: Static documentation review completed; runtime test execution was unavailable in this automation environment.
- Commit hash: pending final commit lookup
- Follow-up notes: Roadmap v1 is complete. Reassess the repository and prepare Roadmap v2 before implementing new work.

## 2026-07-07 — AUTO-005

- Task ID: AUTO-005
- Summary: Documented the repository policy format and added a conservative example policy for future automation boundaries.
- Validation completed: Documentation and example consistency reviewed; runtime test execution was unavailable in this automation environment.
- Commit hash: pending final commit lookup
- Follow-up notes: Run `PYTHONPATH=src python -m pytest` in a checkout-capable environment and proceed to AUTO-006.

## 2026-07-07 — AUTO-004

- Task ID: AUTO-004
- Summary: Added a read-only dry-run repository report command with report-builder and CLI tests.
- Validation completed: Static review completed; runtime test execution was unavailable in this automation environment.
- Commit hash: pending final commit lookup
- Follow-up notes: Run `PYTHONPATH=src python -m pytest` in a checkout-capable environment. Update `.ai/AUTONOMOUS_PLAN.md` to mark AUTO-004 DONE if the connector safety filter continues blocking full-file plan writes.

## 2026-07-07 — AUTO-003

- Task ID: AUTO-003
- Summary: Added deterministic eligible-task selection and exposed the selected TODO task through `forge tasks --next`.
- Validation completed: Static review completed; runtime test execution was unavailable in this automation environment.
- Commit hash: pending final commit lookup
- Follow-up notes: Run `PYTHONPATH=src python -m pytest` in a checkout-capable environment and proceed to AUTO-004.

## 2026-07-07 — AUTO-002

- Task ID: AUTO-002
- Summary: Added deterministic roadmap task parsing and a read-only `forge tasks` command with parser and CLI tests.
- Validation completed: Static review completed; runtime test execution was unavailable in this automation environment.
- Commit hash: pending final commit lookup
- Follow-up notes: Run `PYTHONPATH=src python -m pytest` in a checkout-capable environment and proceed to AUTO-003.

## 2026-07-07 — AUTO-001

- Task ID: AUTO-001
- Summary: Added the initial Python package scaffold, `forge` CLI entry point, README setup notes, smoke test, and decisions log.
- Validation completed: Static review completed; runtime test execution was unavailable in this tool environment.
- Commit hash: pending final commit lookup
- Follow-up notes: Run the documented pytest command in the next checkout-capable run and proceed to AUTO-002.

## 2026-07-07 — Bootstrap

- Task ID: Bootstrap
- Summary: Added the initial roadmap, state files, README, license, and ignore rules.
- Validation completed: Documentation reviewed; no code exists yet.
- Commit hash: pending
- Follow-up notes: Start AUTO-001 next.
