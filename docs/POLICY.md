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

- `Allowed paths` describes where routine autonomous edits may be considered.
- `Prohibited paths` always wins over `Allowed paths`.
- `Human approval required` lists categories that must be blocked until a person explicitly approves them.
- `Validation expectations` lists checks that should be attempted before a change is committed.

## Conservative defaults

When a policy file is missing, malformed, or ambiguous, Autonomous Forge should treat the repository as documentation-only and avoid implementation work. Future parser behavior should prefer false negatives over unsafe edits.

## Example policy

See `.forge/policy.md` for a minimal example aligned with the current local-first MVP.
