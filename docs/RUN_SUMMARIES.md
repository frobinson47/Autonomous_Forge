# Local Run Summary Format

Autonomous Forge does not automatically write execution history files yet. This document defines the intended local run-summary shape so future write behavior can be reviewed before it is implemented.

The format is deliberately plain Markdown with a small set of stable fields. The current `forge run-summary` command previews this structure on standard output without writing files.

## Safety rules

- A run summary is a record, not proof that validation succeeded.
- A run summary must not contain secrets, tokens, credentials, environment dumps, or private command output.
- A run summary must not include full diffs by default.
- A run summary must not be written automatically until the roadmap explicitly allows write behavior.
- The preview command is read-only and prints the summary to standard output.

## Required fields

Each summary should include these fields:

```text
Run timestamp: <ISO-8601 timestamp with timezone>
Selected task: <AUTO-### — title, or none>
Task status before run: <TODO|DONE|BLOCKED|SKIPPED|unknown>
Policy status: <present and readable|missing|malformed: reason>
Validation plan: <human-readable validation command or review plan>
Validation result: <not run|passed|failed|unavailable: reason>
Changed files summary: <none|short list or placeholder>
Commit: <none|pending|short hash>
Notes: <short human-readable notes>
```

## Example preview

```text
Run timestamp: 2026-07-07T14:00:00+04:00
Selected task: AUTO-011 — Record local run summaries without execution
Task status before run: TODO
Policy status: present and readable
Validation plan: PYTHONPATH=src python -m pytest
Validation result: not run
Changed files summary: none
Commit: none
Notes: Read-only preview only; no run-summary file was written.
```

## Preview command

```bash
forge run-summary --plan .ai/AUTONOMOUS_PLAN.md --policy .forge/policy.md
```

The command reads the roadmap and policy, selects the same next eligible task used by the planner, reports policy readability, and prints placeholder fields for validation result, changed files, and commit. It does not write execution history.

A separate roadmap task is still required before any command writes run summaries to disk.
