# Autonomous State

- Current roadmap version: v7
- Current task ID: AUTO-051 — Replace shell=True in forge validate with safer execution
- Current task status: DONE
- Current branch: main
- Last run timestamp: 2026-07-25T00:00:00+00:00
- Last successful commit hash: 0d9a786
- Latest run summary: `validate.py`'s `run_validation()` no longer unconditionally uses `shell=True`. A quote-aware `_needs_shell()` scanner classifies commands: those with pipes/redirects/chaining/expansion require a new `allow_shell_command` param (CLI: `--allow-shell-command`, default False) and run via shell; everything else is tokenized with `shlex` and run as a plain argv list with `shell=False`. Wired the flag through `run`/`commit`/`pipeline`/`validate` CLI commands. Also documented `forge validate`, which had no docs/COMMANDS.md section before. 379 total tests pass (12 new).
- Validation commands and results: `python -m pytest` — 379 tests pass. `forge lint-plan` — ok.
- Current blockers: None.
- Recommended next task: AUTO-052 — Make .forge/.lock acquisition atomic (close the TOCTOU race in lock.py).
