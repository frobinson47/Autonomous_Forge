# Repository Policy Format

Autonomous Forge policy files describe the safe boundary for future repository automation before any runner changes files. The first supported location is `.forge/policy.md`.

The format is intentionally plain Markdown so humans can review it in pull requests and agents can parse it conservatively later.

## Required sections

A policy file should include these headings:

```markdown
# Autonomous Forge Policy

## Allowed paths

- `src/**`
- `tests/**`
- `docs/**`
- `.ai/**`

## Prohibited paths

- `.env`
- `.env.*`
- `**/*secret*`
- `**/*token*`
- `**/*.pem`
- `**/*.key`

## Human approval required

- Changes to GitHub workflow permissions.
- Changes that add network calls.
- Changes that execute external commands.
- Changes to licensing, repository visibility, or access controls.

## Validation expectations

- Run the narrowest relevant tests first.
- Run the documented full test command before committing when available.
- Record unavailable validation honestly in `.ai/AUTONOMOUS_STATE.md`.
```

## Semantics

- `Allowed paths` describes where routine autonomous edits may be considered. `forge run`, `forge commit`, and `forge pipeline` block by default if a changed file falls outside every allowed pattern (see DEC-012); pass `--advisory-paths` to report such files instead of blocking.
- `Prohibited paths` always wins over `Allowed paths` and is never overridable by `--advisory-paths`.
- `Human approval required` lists categories that a task's own plan entry can self-declare against via an `Approval needed: <category text>` field (see DEC-013). A task with that field set is blocked from `forge run`/`forge commit`/`forge pipeline` until a human runs `forge approve <task-id> "<category>"`, which appends a record to `.forge/approvals.md`. There is no automatic detection — forge does not scan diffs or task prose for these categories; if a task's author forgets to set the field, no gate is applied. This section is only as effective as the honesty of whoever writes each task.
- `Validation expectations` lists checks that should be attempted before a change is committed.

## Conservative defaults

`forge run`, `forge commit`, and `forge pipeline` block by default when `.forge/policy.md` is missing or fails to parse (see DEC-012) — a repo with no readable policy cannot safely be checked against `Allowed paths`/`Prohibited paths`, so mutating commands refuse to proceed rather than silently skipping the check. Pass `--no-policy-required` to explicitly opt out (e.g. during `forge init`'s bootstrap window, before a policy file exists yet).

## Example policy

See `.forge/policy.md` for a minimal example aligned with the current local-first MVP.
