# Autonomous State

- Current roadmap version: v8
- Current task ID: AUTO-067 — Make the Forgejo client configurable and harden its error handling
- Current task status: DONE
- Current branch: main
- Last run timestamp: 2026-08-25T00:00:00+00:00
- Last successful commit hash: (this task's commit — see git log)
- Latest run summary: The Forgejo base URL and repo-detection regex were hardcoded to `forgejo.familytechlab.com`, and the HTTP layer only caught `HTTPError` — DNS/connection/timeout/malformed-JSON failures escaped as raw tracebacks (SEC-006). Made the base URL configurable (`--base-url` CLI flag > `FORGEJO_BASE_URL` env > `.forge/config.toml`'s new `forgejo_base_url` > project default), validated as well-formed `https://`. Added `normalize_repo` to validate `owner/repo` shape before ever building a URL from it. Hardened `ForgejoClient._request` to catch `URLError`/`TimeoutError`/JSON-decode failures alongside the existing `HTTPError` handling, all converted to the same `RuntimeError` every call site already catches. Deliberately kept `ForgejoClient`/`_detect_forgejo_repo`/`_load_token` imported directly into `sync.py`/`sync_orphans.py` (not centralized behind a new helper) to preserve existing tests' module-level mocking pattern.
- Validation commands and results: `python -m pytest` — 476 tests pass (454 baseline + 22 new). `ruff check .` — clean. `mypy` — clean. `forge lint-plan` — ok. Manually verified live: pointing `forge sync` at an unreachable host produced a clean `ERROR: ... could not connect: ...` line instead of a traceback; an `http://` base URL and an invalid repo name both produced clean validation errors.
- Current blockers: None. Unrelated, carried over from AUTO-055: no confirmed CI runner is attached to this repo's Forgejo Actions workflow (0 observed runs) — separate infra work, not blocking the roadmap.
- Recommended next task: AUTO-068 — pin CI and dev-dependency supply chain (next in Roadmap v8's Tier 4).
