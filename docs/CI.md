# CI recipe

`forge check` runs lint, drift, diff-check, and validation in one command and exits non-zero if anything fails — it's the natural gate for a CI job. As of AUTO-055, this repo dogfoods its own recipe: see `.forgejo/workflows/forge-check.yml`, which runs Ruff, mypy, and `forge check` (which itself runs the test suite) on every push and pull request. Adopt the recipe below in your own repo if you want the same checks enforced on every push/PR.

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

The minimal version above is enough on its own. This repo's actual workflow (`.forgejo/workflows/forge-check.yml`) adds two more steps ahead of `forge check`, gated by a `dev` extra declared in `pyproject.toml`:

```yaml
      - name: Install
        run: python -m pip install -e ".[dev]"

      - name: Ruff
        run: ruff check .

      - name: mypy
        run: mypy

      - name: forge check
        run: forge check
```

## What this catches

- **Ruff** (if adopted, see below) — a conservative rule set (`E4`, `E7`, `E9`, `F`, `I`: pyflakes, core pycodestyle errors, import sorting). Configured in `pyproject.toml`'s `[tool.ruff.lint]`, not ruff's own out-of-the-box defaults, which pull in opinionated plugin rule sets (bandit, pylint, flake8-simplify, etc.) that would need their own dedicated cleanup pass to adopt safely.
- **mypy** (if adopted, see below) — static type checking, scoped to `src/autonomous_forge` via `pyproject.toml`'s `[tool.mypy]`.
- **Lint** — malformed roadmap task blocks (`forge lint-plan`).
- **Drift** — plan/state/changelog/policy files disagreeing with each other or the repo, or (as of AUTO-057) README's stated task/test counts drifting from reality (`forge drift`).
- **Diff-check** — changed files outside the policy's allowed paths, or touching prohibited paths (`forge diff-check`).
- **Validation** — the test suite (`python -m pytest` by default, or whatever `.forge/policy.md`'s Validation expectations section specifies).

A failure in any step fails the job.

## Adopting Ruff/mypy in your own repo

Not required — `forge check` alone is a complete, working CI gate with zero extra dependencies. If you want the same lint/type-check layer this repo uses:

```toml
[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "pytest-cov", "ruff", "mypy"]

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I"]

[tool.mypy]
python_version = "3.10"
files = ["src/your_package"]
```

`pytest-cov` is declared for local coverage runs (`pytest --cov=your_package`) but not wired into CI as an enforced threshold — an arbitrary percentage gate without baseline data to justify it would be its own, separate decision.

## Notes

- No `FORGEJO_TOKEN` or other secrets are required — `forge check` never calls the network. `forge sync`/`forge push` are deliberately **not** part of this recipe; CI should verify, not autonomously commit, push, or sync issues.
- Zero *runtime* dependencies means the install step is just `pip install -e .` — no lockfile, no extra CI setup. Dev-only tooling (Ruff, mypy, pytest itself) lives in the optional `dev` extra precisely so the runtime dependency count stays at zero; installing it is opt-in (`pip install -e ".[dev]"`), which is what CI does.
- `forge check` auto-extracts its validation command from `.forge/policy.md`'s "Validation expectations" section (the first `` Run `...` `` line) — no `--cmd` override is normally needed. This repo's own policy specifies `PYTHONPATH=src python -m pytest` since it runs pytest from the source checkout rather than the installed package; a repo installed editable via `pip install -e .` typically just needs the default `python -m pytest`. Override with `forge check --cmd "..."` only if you need something different from what's in your policy file.
- If you add a CI workflow file under `.forgejo/workflows/` (or `.github/workflows/`), remember to add that path to `.forge/policy.md`'s `Allowed paths` too — as of AUTO-049, `forge commit`/`forge run` block by default on any changed file outside the allowlist.
