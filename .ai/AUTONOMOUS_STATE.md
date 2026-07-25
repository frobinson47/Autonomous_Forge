# Autonomous State

- Current roadmap version: v7
- Current task ID: AUTO-049 — Enforce the allowlist - not-allowed violations block by default
- Current task status: DONE
- Current branch: main
- Last run timestamp: 2026-07-25T00:00:00+00:00
- Last successful commit hash: 9056598
- Latest run summary: Added `advisory_paths` (default False) to `execute_run`/`run_pre_flight`/`execute_commit`/`execute_pipeline`, with a `--advisory-paths` CLI override on `run`/`commit`/`pipeline`. A changed file outside `.forge/policy.md`'s Allowed paths now blocks these commands by default instead of only being reported (DEC-012, AUTO-049) — completes the other half of DEC-012 alongside AUTO-048's fail-closed missing/malformed policy handling. Prohibited-path blocking still takes priority and is never overridable. 351 total tests pass (8 new).
- Validation commands and results: `python -m pytest` — 351 tests pass. `forge lint-plan` — ok.
- Current blockers: None.
- Recommended next task: AUTO-050 — Define structured approval semantics for policy's "Human approval required" section (the biggest open design question in Roadmap v7 — confirm the mechanism with the user before implementing).
