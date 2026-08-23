# Autonomous Forge: Security and Completeness Assessment

## Executive summary

Autonomous Forge is a substantive pre-alpha Python CLI, not a toy. It has a broad command surface, clear local artifacts, explicit opt-ins for commit/push/sync, an atomic repository lock, zero runtime package dependencies, and a large test suite. In this checkout, 406 tests passed, Ruff and mypy passed, and Gitleaks found no secrets across 165 commits.

The product is not, however, an autonomous software-improvement system or a security boundary. It does not implement tasks or invoke an AI agent; it selects a plan item and validates, commits, pushes, and syncs changes that already exist. It also executes repository-controlled validation code with the user's full privileges and environment. Its “human approval” mechanism is a self-declared, editable audit note, and its `forge check` path can fail open when policy checking errors. Those limitations are acceptable for a trusted, single-operator workflow tool, but the README needs to state that threat model plainly.

Practical ratings:

- Security for one trusted operator in a trusted repository: **6/10**.
- Security for untrusted repositories, branches, or contributors: **2/10**; do not treat it as a sandbox.
- Completeness as a repository workflow/gating assistant: **7/10**.
- Completeness as an “autonomous software-improvement system”: **3/10**.
- Reddit readiness: **credible alpha after the high-priority fixes and a positioning rewrite**.

No critical remote vulnerability was identified in the reviewed threat model. The main risks are local code execution, misleading safety signals, audit-integrity gaps, and operational robustness.

## Scope and verification

Reviewed the tracked Python package, tests, roadmap/state files, policy, Git hook, Forgejo workflow, and documentation. The security-review reference set had no Python CLI-specific guide, so this assessment applies general Python, subprocess, Git, credential, and local-automation security practices.

Verification performed on 2026-08-23:

- `python -m pytest -q -p no:cacheprovider`: **406 passed** with one pytest-asyncio deprecation warning.
- `ruff check .`: **passed**.
- `mypy`: **passed for 35 source files**.
- `gitleaks git . --redact`: **165 commits scanned; no leaks found**.
- `forge check`: **failed** because untracked `.claude/` and `.graymatter/` files are outside the policy allowlist; lint, drift, and validation passed.
- `ruff check src --select S`: 17 security-rule findings, mostly expected subprocess warnings, plus a meaningful fail-open exception handler in `check.py`.
- Coverage percentage was not obtained because `pytest-cov` was not installed in the active environment. The CI configuration has no coverage threshold.

The working tree already contained untracked `.claude/` and `.graymatter/` directories. They were not changed. The local `main` branch was one commit ahead of `origin/main` at review time.

## High-severity findings

### SEC-001: Validation is full local code execution, not a sandbox

`run_validation` inherits the entire process environment and executes either an argv command or, with an explicit override, a shell command (`src/autonomous_forge/validate.py:87-130`). The default `python -m pytest` also executes arbitrary repository Python code. A malicious repository or branch can therefore read credentials, modify files, invoke network tools, or compromise the current user when `forge run`, `forge check`, `forge commit`, `forge pipeline`, `forge watch`, or `forge validate` reaches validation.

This behavior is inherent to a test runner, but the product language emphasizes “safe” operation without a prominent trusted-repository warning. The shell-metacharacter scanner reduces accidental shell interpretation; it does not make validation safe against malicious code.

Recommended action: publish an explicit threat model near the top of the README and in a `SECURITY.md`: only run Forge in repositories and branches whose executable code and validation policy you trust; Forge is not a sandbox. Consider a future isolated runner/container mode, but do not imply isolation until it exists.

### SEC-002: “Human approval required” is an unauthenticated, self-declared convention

The approval gate exists only when the task author adds `Approval needed:`. `has_approval` accepts any record with the same task ID and does not match the category (`src/autonomous_forge/approvals.py:76-86`). Any process or agent able to edit the repository or run `forge approve` can create the record (`src/autonomous_forge/approvals.py:89-114`). The decision record acknowledges this limitation, but the README says the policy defines categories “requiring explicit human approval” without the same qualification.

The gate can also be bypassed by putting risky changes under a task that omits the field. Actual changed files are not checked against the task's Scope, Expected files, or approval category.

Recommended action: describe this as an auditable operator attestation, not authenticated human approval. At minimum, require exact task/category matching and record an approver identity supplied by a trusted outer system. Longer term, bind approval to a plan/diff digest so an approval cannot be reused after the proposed change changes.

### SEC-003: `forge check` can report success when policy validation did not run

`execute_check` only performs diff policy checks if the policy file exists (`src/autonomous_forge/check.py:89-96`). It then catches every exception and silently leaves `diff_ok=True` (`src/autonomous_forge/check.py:97-98`). A missing, unreadable, malformed, or internally failing policy check can therefore become a PASS. This contradicts the README statement that `forge check` enforces policy (`README.md:11`).

The mutating `run` and `commit` paths have better fail-closed defaults; this finding is specifically about the advertised all-in-one verification command and CI signal.

Recommended action: make missing/malformed policy and any policy-check exception explicit failures. Catch narrow exception types, include the error in output, and add regression tests for missing policy, malformed policy, Git failure, unreadable files, and unexpected checker exceptions.

### SEC-004: Validation output is persisted without secret redaction

Validation captures stdout/stderr (`src/autonomous_forge/validate.py:122-137`), `execute_run` retains their tail (`src/autonomous_forge/run.py:301-318`), and run summaries write that output verbatim (`src/autonomous_forge/run.py:416-427`). The directory is gitignored, which is good, but a test or tool that prints a token can leave it on disk or expose it through copied diagnostic bundles.

Recommended action: document the risk, add best-effort redaction for common credential formats and configured secret values, restrict run-file permissions where supported, and provide a no-output-persistence mode. Do not claim complete secret detection.

## Medium-severity findings

### SEC-005: Auto-generated changelog content bypasses commit pre-flight policy checking

Commit pre-flight checks the currently staged files (`src/autonomous_forge/commit.py:125-190`). After pre-flight reports safe, `execute_commit` may modify and stage `.ai/AUTONOMOUS_CHANGELOG.md`, then commit it without re-running policy or validation (`src/autonomous_forge/commit.py:276-296`). A repository whose policy does not allow, or explicitly prohibits, that path can still have it added to the commit.

Recommended action: generate and stage the changelog before the final staged-diff policy check, then validate the exact staged tree that will be committed. Check the return code of `git add` as well.

### SEC-006: Forgejo transport is fragile and instance-specific

Repository detection and API URLs are hardcoded to `forgejo.familytechlab.com` (`src/autonomous_forge/forgejo_client.py:15-29` and `:55-75`). This makes the advertised Forgejo integration unusable for normal external adopters. The HTTP layer catches `HTTPError` only (`src/autonomous_forge/forgejo_client.py:74-81`); DNS failures, refused connections, TLS failures, timeouts, malformed JSON, and unexpected response shapes can escape as tracebacks because sync generally catches only `RuntimeError`.

Recommended action: configure and validate an HTTPS base URL, normalize/validate owner and repository names, handle `URLError`, timeout, decode, and schema failures, and return consistent CLI errors. Add retry/backoff only for idempotent reads or with careful operation-specific semantics.

### SEC-007: CI and development dependencies are not reproducible or supply-chain hardened

The build backend, all dev tools, the container image, OS packages, and `actions/checkout@v4` are unpinned (`pyproject.toml:1-3`, `:25-32`; `.forgejo/workflows/forge-check.yml:9-22`). This is common for an alpha, but it means a clean build can change without a repository change. The configured Ruff rules deliberately omit security rules (`pyproject.toml:44-49`).

Recommended action: pin the action by commit digest, pin or lock development dependencies, pin the container by digest for releases, add a security static-analysis job, and use dependency update automation. Avoid presenting this as hardened CI until a runner has actually executed it.

### SEC-008: Git/check failures are sometimes converted to empty or successful results

Several Git helpers return empty stdout without checking nonzero return codes; `get_changed_files` can therefore treat Git failure as no changes (`src/autonomous_forge/diffcheck.py:22-50`). In commit pre-flight that usually blocks as “No changed files,” but in reports and `forge check` it can create a false clean signal. Broad or narrow exception suppression appears in other read paths as well.

Recommended action: represent subprocess outcomes explicitly, distinguish “no changes” from “could not inspect changes,” and fail closed anywhere the result gates a mutation or CI success.

## Functional and completeness gaps

### COMP-001: The core product does not perform autonomous implementation

The roadmap states that the tool is “not ... an autonomous executor” (`.ai/AUTONOMOUS_PLAN.md:7-9`), while the README calls it a tool for “autonomous software-improvement loops” (`README.md:3`). The implementation selects a task, inspects the current diff, runs validation, and optionally commits/pushes/syncs. It does not invoke an agent, apply a task, generate a patch, or manage an implementation loop.

This is the single biggest Reddit-positioning risk. The honest category is “local-first workflow and guardrails for human- or agent-authored repository changes.” That is still useful, but it is a different product.

### COMP-002: A selected task is not bound to the committed diff

The selected TODO supplies a commit message and approval lookup, but Forge does not verify that staged changes correspond to that task's Scope or Expected files. Unrelated staged changes can be committed under the selected task ID. An unstaged plan can also influence task selection while the staged commit contains something else.

Recommended action: record a candidate staged-tree digest and explicit file set for the task, compare it immediately before commit, and optionally enforce declared expected paths. At minimum, disclose that task attribution is conventional rather than verified.

### COMP-003: Pipeline sync errors violate the documented exit-code contract

`execute_pipeline` records sync errors in `stopped_reason` (`src/autonomous_forge/pipeline.py:222-235`), but `_cmd_pipeline` checks run, commit, and push failures only, then returns zero (`src/autonomous_forge/cli.py:1262-1269`). The command reference promises exit code 1 for sync errors. There is no regression test for this case.

Recommended action: return 1 when `sync_result.errors` is nonempty and add a CLI-level test.

### COMP-004: Dogfooding and metadata consistency are currently overstated

The README and state say 401 tests, while 406 passed in this review (`README.md:21`; `.ai/AUTONOMOUS_STATE.md:9-10`). The plan's own status paragraph still says 47 tasks and 329 tests (`.ai/AUTONOMOUS_PLAN.md:15-17`). `forge drift` passes because it compares the README's test count to the equally stale state count; it does not verify pytest's collected/passed count (`src/autonomous_forge/drift.py:155-169`). The old codebase assessment still presents 317 tests as current (`docs/CODEBASE_ASSESSMENT.md:1-9`).

`forge check` also fails in this working copy because `.claude/` and `.graymatter/` local artifacts are not ignored. The state file says the checked-in CI workflow had zero observed runs and likely no attached runner (`.ai/AUTONOMOUS_STATE.md:11`), so “CI, dogfooded” is not yet demonstrated.

Recommended action: update or archive stale assessments, derive counts from machine-readable output rather than prose-to-prose comparison, verify CI on a real runner, and make local tool-state exclusions intentional.

### COMP-005: Release and adopter readiness are still pre-alpha

There are no release tags, no verified package-build/publish path, no `SECURITY.md`, no compatibility matrix in CI, no coverage threshold, and no project URLs in package metadata. Only Python 3.12 is used in the workflow although metadata claims 3.10-3.12 support. The CLI is also concentrated in a 1,500-line `cli.py`, which raises the chance of inconsistent exit codes and options as commands grow.

These are normal alpha gaps, but the Reddit post should say “seeking design and threat-model feedback,” not imply production readiness.

## What is already good

- Zero runtime Python dependencies materially reduces package supply-chain exposure.
- Most subprocess calls use argv lists, not shell strings.
- Commit, push, and sync are separate opt-ins; normal push behavior does not invoke rebase or force-push.
- `run` and `commit` now fail closed by default for missing/malformed policy and outside-allowlist changes.
- The repository lock uses atomic exclusive creation and has cross-platform liveness handling.
- The test suite is broad and includes some real-Git integration tests, not only parser unit tests.
- Ruff, mypy, and the full test suite pass.
- No secrets were found in 165 commits by Gitleaks.
- The project has no server, listener, telemetry, or broad remote execution surface.
- The roadmap, decision records, and local Markdown artifacts make design intent unusually inspectable.

## Before posting to Reddit

Do these first:

1. Reframe the README and post: “workflow guardrails for human/agent-authored changes,” explicitly not an agent runner or sandbox.
2. Fix `forge check` to fail closed on missing/malformed policy and inspection errors.
3. Fix pipeline sync failures returning exit code 0.
4. Move changelog generation before the final policy/validation check.
5. Make the Forgejo base URL configurable or label the integration as instance-specific.
6. Replace “human approval enforcement” language with the exact trusted-operator/self-declaration model, and add a threat model.
7. Update the 401/329/317 test counts, archive the historical assessment, verify CI, and make `forge check` green in a clean/public checkout.
8. Push or intentionally drop the local commit that is currently ahead of `origin/main` before linking the remote.

Then post it. A defensible pitch would be:

> I built a dependency-free Python CLI that adds repository-native planning, policy checks, validation, auditable run records, and opt-in commit/push/Forgejo sync around changes made by humans or coding agents. It is not an autonomous executor or a sandbox. I am looking for feedback on the threat model, task-to-diff binding, and whether the Markdown-first workflow is useful.

That framing invites useful criticism without handing commenters an easy “this is not autonomous” rebuttal.
