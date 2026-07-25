# CI recipe

`forge check` runs lint, drift, diff-check, and validation in one command and exits non-zero if anything fails — it's the natural gate for a CI job. This is a documented recipe, not a workflow file added to this repo: `forge watch` already covers local, between-session checks, and there is no `.forgejo/workflows/` or `.github/workflows/` directory here. Adopt the recipe below in your own repo if you want the same checks enforced on every push/PR.

The workflow YAML below works for either **Forgejo Actions** or **GitHub Actions** — the syntax is compatible. Only the directory differs:

- Forgejo Actions: `.forgejo/workflows/forge-check.yml`
- GitHub Actions: `.github/workflows/forge-check.yml`

```yaml
name: forge check

on:
  push:
  pull_request:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install
        run: python -m pip install -e .

      - name: forge check
        run: forge check
```

## What this catches

- **Lint** — malformed roadmap task blocks (`forge lint-plan`).
- **Drift** — plan/state/changelog/policy files disagreeing with each other or the repo (`forge drift`).
- **Diff-check** — changed files outside the policy's allowed paths, or touching prohibited paths (`forge diff-check`).
- **Validation** — the test suite (`python -m pytest` by default, or whatever `.forge/policy.md`'s Validation expectations section specifies).

A failure in any of the four fails the job — `forge check` exits `1` if any check fails, `0` only if all pass.

## Notes

- No `FORGEJO_TOKEN` or other secrets are required — `forge check` never calls the network. `forge sync`/`forge push` are deliberately **not** part of this recipe; CI should verify, not autonomously commit, push, or sync issues.
- Zero runtime dependencies means the install step is just `pip install -e .` — no lockfile, no extra CI setup.
- `forge check` auto-extracts its validation command from `.forge/policy.md`'s "Validation expectations" section (the first `` Run `...` `` line) — no `--cmd` override is normally needed. This repo's own policy specifies `PYTHONPATH=src python -m pytest` since it runs pytest from the source checkout rather than the installed package; a repo installed editable via `pip install -e .` typically just needs the default `python -m pytest`. Override with `forge check --cmd "..."` only if you need something different from what's in your policy file.
