# Autonomous Forge — Codebase Assessment

## Executive summary

Autonomous Forge is a small, well-tested Python CLI for repository maintenance workflows. It excels at making agent/human work explicit, reviewable, and local-first: a Markdown roadmap determines the next task; Git diff checks and validation precede committing; higher-impact actions require explicit flags.

Its main weakness is a gap between its safety narrative and its enforcement. Several documented policy guarantees are advisory or inconsistently applied, while the tool can execute shell commands, commit, push, and modify Forgejo issues. It is a strong pre-1.0 workflow assistant, but not yet a robust “safe autonomous maintenance” system.

Verification: `317 passed` in 19.02 seconds. No files were changed during the assessment itself.

## What it is

The package is a dependency-free Python 3.10+ CLI:

```text
Markdown roadmap + policy
          ↓
task selection / lint / drift / diff checks
          ↓
validation command
          ↓
optional commit → push → Forgejo issue sync
          ↓
local run history, metrics, session handoff
```

Key modules:

- `plan.py`: parses task blocks and deterministically picks the highest-priority TODO.
- `policy.py` and `diffcheck.py`: parse path policy and compare changed files to it.
- `run.py`, `commit.py`, `pipeline.py`: orchestrate validation and Git stages.
- `sync.py`: manages one-way plan-to-Forgejo issue synchronization.
- `session.py`, `context.py`, `metrics.py`: support continuity and reporting.
- `cli.py`: command-line surface; currently the largest module at ~39 KB.

## Where it excels

- Clear product boundary. The project deliberately avoids becoming a hosted executor or deployment platform. The local-first design is appropriate for a tool that can eventually commit and push code.

- Good workflow ergonomics. `forge status`, `context`, `pause`, `resume`, `check`, `watch`, and run history address the real friction of resuming work and maintaining project context.

- Deterministic task selection. Priority plus source-order tie-breaking is simple, explainable, and easy to trust.

- Strong test coverage for its size. The suite is broad across individual commands and key Git/Forgejo flows, including some real-Git integration tests.

- Conservative Git behavior. Pushes are ordinary pushes: no rebase, merge, or force-push behavior is hidden inside the tool. Failed pushes stop loudly.

- Useful auditable artifacts. Human-readable Markdown plans, policies, sessions, run summaries, and changelogs make the workflow inspectable without a proprietary datastore.

- Sensible operational separation. Commit, push, and sync each need separate explicit flags in the pipeline. That is a strong default for pre-1.0 automation.

## Where it fails or is fragile

### 1. Policy enforcement is incomplete

This is the most important issue.

The policy’s “Human approval required” section is parsed but is not enforced as an actionable gate; it is only surfaced in context/reporting. A policy may say network access, external commands, or telemetry need approval, but the tool has no structured approval record or mechanism that checks a proposed action against that requirement.

More importantly, a missing or malformed policy does not reliably prevent mutation:

- `run.py` reports missing/malformed policy but can continue.
- `commit.py` only checks policy rules if policy text exists; when the policy is absent, it can still validate and consider a staged commit safe.
- This conflicts with the documented conservative default that ambiguous policy should prevent implementation work.

Impact: the strongest advertised safety boundary can silently disappear in an incompletely initialized or damaged repository.

### 2. Validation executes arbitrary shell text

`validate.py` runs the validation command with `shell=True`. The command may come from a CLI flag or be extracted from a Markdown policy bullet.

This is convenient, but it means anyone who can edit the policy file—or influence a passed command—can cause arbitrary local shell execution when a user runs `forge check`, `run`, `commit`, or `pipeline`.

For a personal trusted repository this may be acceptable. For shared repositories, agent workflows, or unreviewed branches, it substantially weakens the safety posture.

### 3. Run and commit have inconsistent policy semantics

`forge run` detects all diff violations but blocks only prohibited files. Files outside allowed paths can be reported yet still allow the run to progress. `forge commit` similarly collects non-prohibited violations yet still returns `safe=True`.

That makes “Allowed paths” advisory rather than an allowlist. The documentation and policy vocabulary imply stronger enforcement than the code provides.

### 4. Locking is not atomic

The lock implementation checks whether `.forge/.lock` exists, then writes it with `write_text`. Two processes can both observe no lock and both create one. The lock reduces common contention but does not guarantee mutual exclusion.

A process-safe primitive such as atomic exclusive creation is needed if concurrent agents are a real use case.

### 5. The Markdown formats are intentionally simple but brittle

The custom parser is understandable, but it carries scaling and correctness limits:

- Task IDs are fixed to `AUTO-\d{3}`, so the model stops working naturally after `AUTO-999`.
- The plan parser only requires `Priority` and `Status`; more complete structure is enforced separately by linting, but normal execution does not require lint to pass first.
- Repeated fields silently overwrite earlier values.
- The strict policy parser allows only section headings and bullets, making reasonable Markdown elaboration fail parsing.

This is fine for a controlled internal workflow, but it is brittle as a reusable tool.

### 6. The CLI and Forgejo sync module are becoming monoliths

`cli.py` (~39 KB) and `sync.py` (~24 KB) contain growing amounts of dispatch/orchestration behavior. This makes additions increasingly likely to create output, exit-code, and safety inconsistencies across commands.

The Forgejo integration also directly owns HTTP behavior, issue matching, labels, milestones, and import logic in one place. It needs clearer boundaries before more integrations are added.

### 7. Documentation and project state are stale

The README reports Roadmaps v1–v4 complete with 37 tasks and 253 tests. The current plan contains Roadmap v6, 46 completed tasks plus `AUTO-047` TODO, and the current suite has 317 passing tests.

For a project whose purpose is preventing metadata drift, this is especially damaging: it undermines confidence in the tool’s own dogfooding.

### 8. Developer tooling is minimal

`pyproject.toml` has no declared development dependencies, test extras, formatter, linter, type checker, coverage target, or real CI workflow. The repository documents a CI recipe but does not itself enforce it.

The test suite catches functional regressions well, but the project has limited automated guardrails for style, types, documentation consistency, dependency security, or release quality.

## Improvements, in priority order

1. Make policy fail closed for all mutating commands. Missing, malformed, or empty policy should block `commit`, `pipeline --commit`, `mark`, `plan add`, `init` where applicable, and orphan import unless an explicit, prominently named override is supplied.

2. Define real approval semantics. Replace prose-only “Human approval required” entries with structured policy rules and an explicit approval mechanism, such as an approved task ID, signed/recorded approval note, or required interactive confirmation scoped to an action.

3. Enforce the allowlist. Treat both prohibited paths and paths outside `Allowed paths` as commit-blocking by default. If advisory mode is desired, make it explicit.

4. Replace `shell=True` with command-array execution where possible. For custom commands, require an explicit `--allow-shell-command` flag or make the command a structured list in configuration rather than Markdown prose.

5. Make locking atomic. Use exclusive creation (`O_CREAT | O_EXCL`) or a mature cross-platform lock library. Include owner metadata and a safe stale-lock recovery strategy.

6. Require plan linting before mutable pipeline stages. A malformed plan should never be used to select, commit against, or sync tasks.

7. Split orchestration layers. Keep CLI parsing thin; move per-command handlers into modules. Separate Forgejo transport, reconciliation logic, and plan-import behavior.

8. Add a real CI workflow and development quality checks. At minimum: test matrix for supported Python versions, Ruff, a type checker, coverage reporting, and a documentation/metadata consistency check.

9. Treat the roadmap as a scale-limited first implementation. Either expand ID handling now or document and test a migration path before task 1,000.

10. Fix repository self-consistency immediately. Update README status/test counts, record the remaining TODO in the state file, and add a check that catches stale headline statistics.

## Bottom line

This is a thoughtful and practical foundation for repository-native maintenance workflows. Its strongest qualities are transparency, deterministic behavior, and good functional tests. The next stage should focus less on adding commands and more on making its current safety contract mechanically true—especially around missing policy, allowlist enforcement, approval requirements, shell execution, and concurrency.
