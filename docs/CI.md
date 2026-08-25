# CI recipe

`forge check` runs lint, drift, diff-check, and validation in one command and exits non-zero if anything fails — it's the natural gate for a CI job. As of AUTO-055, this repo dogfoods its own recipe: see `.forgejo/workflows/forge-check.yml`, which runs Ruff, mypy, and `forge check` (which itself runs the test suite) on every push and pull request. Adopt the recipe below in your own repo if you want the same checks enforced on every push/PR.

The workflow YAML below works for either **Forgejo Actions** or **GitHub Actions** — the syntax is compatible. Only the directory differs:

- Forgejo Actions: `.forgejo/workflows/forge-check.yml`
- GitHub Actions: `.github/workflows/forge-check.yml`

**`runs-on:` must match a label your runner actually registered with.** `ubuntu-latest` is a GitHub-hosted-runner label; a self-hosted Forgejo runner (`act_runner`/`forgejo-runner`) only claims jobs whose `runs-on:` matches one of its own configured labels (commonly `docker` or `self-hosted` — check the runner's `runner.labels` config, or the label shown when it was registered). A workflow with a `runs-on:` value no runner advertises just sits queued forever with zero visible error. This repo's own workflow uses `runs-on: docker` for exactly this reason.

**`actions/setup-python@v5` can fail on self-hosted runners** with `Version 3.12 was not found in the local cache` / `was not found for this operating system` — it expects either a pre-warmed tool cache or a working path to GitHub's `python-versions` release manifest, neither of which a bare self-hosted runner has by default. Simplest fix: skip `setup-python` and run the job in a container image that already has the right Python (`container: image: python:3.12`), as this repo's workflow does below. That image has neither `git` nor `node`, though, and `actions/checkout@v4` is a Node.js action — install both before the checkout step.

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

The minimal version above works as a starting point on a GitHub-hosted-style runner. This repo's actual workflow (`.forgejo/workflows/forge-check.yml`) looks different because of the two self-hosted-runner gotchas above, plus two more steps ahead of `forge check` gated by a `dev` extra declared in `pyproject.toml`, plus an advisory security-rules step and digest-pinned action/image references (AUTO-068 / SEC-007 — see the workflow file itself for the full comments explaining each pin):

```yaml
jobs:
  check:
    runs-on: docker
    container:
      image: python:3.12@sha256:ef1735ee20f31133880795148379e68f8fe12f4b7a1872075477567f022edc1f
    steps:
      - name: Install git and node
        run: apt-get update && apt-get install -y --no-install-recommends git nodejs

      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262  # v4.4.0

      - name: Install
        run: python -m pip install -e ".[dev]"

      - name: Ruff
        run: ruff check .

      - name: mypy
        run: mypy

      - name: forge check
        run: forge check

      - name: Ruff security rules (advisory)
        continue-on-error: true
        run: ruff check src --select S
```

The `python:3.12` image and `actions/checkout` are pinned by digest, not the floating `python:3.12`/`v4` tags — a clean CI run today should build the same environment tomorrow, and neither reference changes without a deliberate repository commit. Re-pin (bump the digest) intentionally, e.g. to pick up a Python patch release or a newer checkout action — never let it drift silently.

## What this catches

- **Ruff** (if adopted, see below) — a conservative rule set (`E4`, `E7`, `E9`, `F`, `I`: pyflakes, core pycodestyle errors, import sorting). Configured in `pyproject.toml`'s `[tool.ruff.lint]`, not ruff's own out-of-the-box defaults, which pull in opinionated plugin rule sets (bandit, pylint, flake8-simplify, etc.) that would need their own dedicated cleanup pass to adopt safely.
- **mypy** (if adopted, see below) — static type checking, scoped to `src/autonomous_forge` via `pyproject.toml`'s `[tool.mypy]`.
- **Lint** — malformed roadmap task blocks (`forge lint-plan`).
- **Drift** — plan/state/changelog/policy files disagreeing with each other or the repo, or (as of AUTO-057) README's stated task/test counts drifting from reality (`forge drift`).
- **Diff-check** — changed files outside the policy's allowed paths, or touching prohibited paths (`forge diff-check`).
- **Validation** — the test suite (`python -m pytest` by default, or whatever `.forge/policy.md`'s Validation expectations section specifies).
- **Coverage** — `pytest --cov=autonomous_forge`, gated by an 80% floor (`fail_under` in `pyproject.toml`'s `[tool.coverage.report]`, AUTO-071).
- **Ruff security rules (advisory only)** — `ruff check src --select S` (the flake8-bandit rule set), run as a separate, non-blocking step (`continue-on-error: true`). Findings are visible in CI output but never fail the job — adopting the full rule set as blocking would be a separate, deliberate decision (see AUTO-055's note on Ruff's out-of-the-box defaults surfacing 93 unadopted findings).

A failure in any step (except the advisory security-rules step) fails the job.

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

`pytest-cov` is declared for local coverage runs (`pytest --cov=your_package`). This repo enforces a floor via `[tool.coverage.report]`'s `fail_under` in `pyproject.toml` (AUTO-071) — set to 80%, deliberately well below the 89% baseline measured when it was added, so it catches a real regression (a large new module with no tests at all) rather than blocking ordinary small refactors on every minor coverage wobble. If you adopt this recipe elsewhere, pick your own threshold from your own baseline (`pytest --cov=your_package --cov-report=term-missing` first, then set `fail_under` with real headroom below whatever that reports) — don't copy `80` as a default without checking what your own suite actually covers.

Pin these to exact versions (`pytest==8.3.3`, not `pytest`) once you've settled on a working set — an unpinned `dev` extra means a clean `pip install -e ".[dev]"` can silently pick up a newer tool version and change what CI enforces (AUTO-068 / SEC-007).

## Notes

- No `FORGEJO_TOKEN` or other secrets are required — `forge check` never calls the network. `forge sync`/`forge push` are deliberately **not** part of this recipe; CI should verify, not autonomously commit, push, or sync issues.
- Zero *runtime* dependencies means the install step is just `pip install -e .` — no lockfile, no extra CI setup. Dev-only tooling (Ruff, mypy, pytest itself) lives in the optional `dev` extra precisely so the runtime dependency count stays at zero; installing it is opt-in (`pip install -e ".[dev]"`), which is what CI does.
- `forge check` auto-extracts its validation command from `.forge/policy.md`'s "Validation expectations" section (the first `` Run `...` `` line) — no `--cmd` override is normally needed. This repo's own policy specifies `PYTHONPATH=src python -m pytest` since it runs pytest from the source checkout rather than the installed package; a repo installed editable via `pip install -e .` typically just needs the default `python -m pytest`. Override with `forge check --cmd "..."` only if you need something different from what's in your policy file.
- If you add a CI workflow file under `.forgejo/workflows/` (or `.github/workflows/`), remember to add that path to `.forge/policy.md`'s `Allowed paths` too — as of AUTO-049, `forge commit`/`forge run` block by default on any changed file outside the allowlist.
