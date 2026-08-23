# Autonomous State

- Current roadmap version: v8
- Current task ID: AUTO-058 — Fix forge check's fail-open policy-diff exception handling
- Current task status: DONE
- Current branch: main
- Last run timestamp: 2026-08-23T00:00:00+00:00
- Last successful commit hash: (this task's commit — see git log)
- Latest run summary: Roadmap v8 (AUTO-058 through AUTO-069) was added from an external security/completeness assessment (`docs/SECURITY_ASSESSMENT_2026-08-23.md`, see DEC-015). AUTO-058 is the first task completed: `forge check`'s diff-policy check no longer fails open on a missing, malformed, or unreadable policy file — it now fails closed by default (matching `forge run`/`forge commit`'s existing `require_policy` pattern), with a new `--no-policy-required` override on both `forge check` and `forge watch`. Also fixed an adjacent crash: the Drift block's own policy read only caught `FileNotFoundError`, so an unreadable (not missing) policy file crashed the whole command before reaching the diff-check block — widened to catch `OSError`.
- Validation commands and results: `python -m pytest` — 411 tests pass (406 baseline + 5 new for AUTO-058). `ruff check .` — clean. `mypy` — clean. `forge lint-plan` — ok. Manually verified in a throwaway repo: malformed/missing policy → `forge check` exit 1 with a clear message; `--no-policy-required` restores exit 0.
- Current blockers: None. Unrelated, carried over from AUTO-055: no confirmed CI runner is attached to this repo's Forgejo Actions workflow (0 observed runs) — separate infra work, not blocking the roadmap.
- Recommended next task: AUTO-059 — return exit code 1 when `forge pipeline` sync fails (same "tool misreports its own pass/fail" class of bug as AUTO-058, next in Roadmap v8's Tier 1).
