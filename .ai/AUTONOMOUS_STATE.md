# Autonomous State

- Current roadmap version: v8
- Current task ID: AUTO-060 — Distinguish "no changes" from "could not inspect changes" in Git helpers
- Current task status: DONE
- Current branch: main
- Last run timestamp: 2026-08-23T00:00:00+00:00
- Last successful commit hash: (this task's commit — see git log)
- Latest run summary: `get_changed_files`/`_run_git` in `diffcheck.py` silently returned an empty result on any git failure (not a repo, git missing, timeout), indistinguishable from "genuinely no changes" — a false-clean signal that `forge check`/`forge run`/`forge diff-check` could report as PASS, and that `forge commit` only happened to block by accident (via the wrong "No changed files" message). Added `GitCommandError`, raised by `_run_git` on any failure; `check.py`, `commit.py`, `run.py`, and `read_diff_report` now catch it explicitly and fail closed with a distinct, honest message. Audited all 12 `subprocess.run` sites in the package; found one more instance of the same shape (`session.py`'s `_run_git`, used only by `forge pause`'s informational git snapshot) and deliberately left it as-is since nothing downstream treats its result as a gating signal — documented the reasoning in AUTO-060's Risks note rather than silently fixing everything found. Also added a `forge diff-check` docs section (previously undocumented) since its exit-code contract changed.
- Validation commands and results: `python -m pytest` — 417 tests pass (412 baseline + 5 new). `ruff check .` — clean. `mypy` — clean. `forge lint-plan` — ok. Manually verified against a real non-git directory: `forge diff-check` and `forge check` report the specific git error and exit 1; `forge commit` blocks with "Could not determine changed files" instead of the misleading "No changed files to commit."
- Current blockers: None. Unrelated, carried over from AUTO-055: no confirmed CI runner is attached to this repo's Forgejo Actions workflow (0 observed runs) — separate infra work, not blocking the roadmap.
- Recommended next task: AUTO-061 — move changelog staging before the final commit policy check (start of Roadmap v8's Tier 2; also where `commit.py`'s own separate `_run_git`/`git add` return-code handling, deliberately left untouched by AUTO-060, belongs).
