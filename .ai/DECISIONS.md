# Autonomous Decisions

## DEC-015 — 2026-08-23 — Roadmap v8 sourced from external security/completeness assessment

Context: `docs/SECURITY_ASSESSMENT_2026-08-23.md`, an external security and completeness assessment run against this repo (2026-08-23), found 4 high-severity and 4 medium-severity security findings plus 5 completeness/positioning gaps. No critical remote vulnerability was found — findings are local code execution, misleading safety signals, audit-integrity gaps, and operational robustness, consistent with the project's own stated single-trusted-operator, local-first scope.
Decision: Convert every finding into a tracked AUTO-xxx task (AUTO-058 through AUTO-069, Roadmap v8), grouped into four tiers by dependency rather than by the report's own high/medium/completeness split: (1) fail-closed correctness bugs — `forge check`'s fail-open policy exception, `forge pipeline`'s wrong exit code, Git failure/no-changes conflation; (2) policy-ordering fixes — changelog staging order, task-to-diff binding; (3) documentation/positioning — threat model, `SECURITY.md`, README reframing away from "autonomous executor," stale test-count metadata; (4) robustness/hardening — secret redaction in persisted output, Forgejo client configurability, CI supply-chain pinning, alpha-readiness polish. Recommended sequence: Tier 1 → Tier 3 → Tier 2 → Tier 4, since Tier 1 fixes the worst category (the tool misreporting its own pass/fail) and Tier 3 is pure documentation that unblocks honest external positioning fastest, independent of code changes.
Alternatives considered: (a) Work strictly in the report's own high-then-medium severity order — rejected because two "high" findings (SEC-001 sandbox expectations, SEC-002 approval authentication) are accepted, disclosed-tradeoff design decisions for a trusted-operator tool, not bugs to fix in code, while two "medium" findings (SEC-003's fail-open exception, COMP-003's wrong exit code) are straightforward bugs that actively mislead users about pass/fail state right now — code-correctness urgency doesn't track the report's severity labels one-to-one. (b) Treat AUTO-062 (task-to-diff binding, COMP-002) as a normal bugfix task like the others — rejected; it's flagged as a design decision requiring explicit warn-vs-block sign-off before implementation, per this project's "ask, don't assume" default, since it changes commit UX for every existing workflow.
Consequences: Twelve new TODO tasks added to the plan (AUTO-058–069), none yet implemented. AUTO-058 (forge check fail-open) and AUTO-059 (pipeline exit code) are the highest-priority items in the whole roadmap by "does the tool lie about its own success" standard, ahead of the pre-existing sequential task ordering. AUTO-062 is explicitly gated on a follow-up discussion before code is written.
Human decision still required: No for creating and tracking the tasks — this decision record is that sign-off (user reviewed the report and asked for a plan, then approved writing it into the roadmap). Yes, separately, for AUTO-062's strictness (warn vs. block) before that specific task is implemented.

## DEC-014 — 2026-07-31 — `forge sync` matches issues via Notes backlink before title

Context: In repos where every AUTO-xxx task was already backed by a real, pre-existing Forgejo issue with a title that follows neither the `[AUTO-xxx] Title` nor legacy `AUTO-xxx: Title` convention (e.g. bulk-imported before `forge sync` existed, or hand-filed with unrelated titles), `_find_issue_for_task`'s title-only matching found nothing and every `forge sync` either offered to create a full set of duplicate issues or had to be skipped entirely. Skipping punts the problem: the same "would-create N duplicates" surprise recurs on every future sync for anyone who doesn't remember why it was skipped. `--import-orphans` already solved an adjacent version of this (recognizing an issue it previously imported) via a `Forgejo issue #N` backlink written into the task's Notes field, but `execute_sync`'s own matching never read that field.
Decision: Unify the two: `_find_issue_for_task` now checks a task's Notes field for a `Forgejo issue #N` backlink first, and only falls back to title matching if none is found. A backlink match wins outright regardless of the issue's actual title. This is a root-cause fix in the shared tool (`autonomous_forge/sync.py`), not a per-repo workaround, so every repo using this tool benefits, not just the one that surfaced the gap. Repos with unmatched legacy issues need a one-time `Notes: ... Forgejo issue #N ...` line added per task (by hand, or via `--import-orphans` for issues still open and orphaned) to stop future syncs from offering to create duplicates.
Alternatives considered: (a) Fix it only in the affected repo (e.g. a local script or one-off manual issue linking) — rejected as the most tactical option: it doesn't help the ~16 other repos sharing this tool, and the identical surprise recurs wherever else pre-existing issues predate `forge sync`. (b) Fuzzy title matching (Levenshtein/substring) between task title and issue title — rejected as unreliable and silently wrong in a way an explicit backlink isn't; a near-miss match could silently attach the wrong issue to a task. (c) Require an issue-number field in the plan task header itself (e.g. `Issue: #42`) instead of reusing the Notes-field convention — rejected as a parallel data path when the Notes-field backlink already exists, is git-tracked, and is proven by `--import-orphans`'s own idempotency check (`_issue_already_imported`).
Consequences: Sync correctness now depends on the backlink text being well-formed (`Forgejo issue #N`, matching `_ISSUE_BACKLINK_RE`) and present in the task's block. No verification that the backlinked issue is actually related to the task beyond the number existing in the fetched issue list — same trust model as every other self-reported plan field (see DEC-013). Existing repos with unlinked legacy issues still see one round of "would-create" until backlinks are added; this doesn't retroactively scan and match issues by content.
Human decision still required: No — fixing a matching-logic gap in a shared, already-established mechanism (Notes-field backlinks) is ordinary maintenance of existing conventions, not a new policy or safety-relevant behavior change.

## DEC-013 — 2026-07-25 — Self-declared task field + recorded approval file for "Human approval required" (AUTO-050)

Context: DEC-012 (AUTO-048, AUTO-049) fixed both path-based fail-open gaps in policy enforcement, but explicitly left AUTO-050 — enforcing the policy's `Human approval required` section — unresolved as a separate, harder design question. Unlike `Allowed`/`Prohibited paths`, which are file-glob patterns amenable to mechanical string matching, `Human approval required` categories (e.g. "adding network access", "adding telemetry") are behavioral/semantic — detecting them from a diff would require real code/content analysis, which this project deliberately avoids (dependency-free, pattern-matching only, no AST parsing or LLM calls in the core tool).
Decision: Confirmed with the user before implementing (three alternatives presented, see below). Chose a self-declared task field: an optional `Approval needed: <category text>` field on a plan task's block. If set, `forge run`/`forge commit`/`forge pipeline` block that task by default until a matching record exists in a new git-tracked `.forge/approvals.md` file, written only by a new `forge approve <task-id> "<category>" [--note "..."]` command. No content/diff analysis is performed — detection relies on whoever writes the task being honest about it, the same trust model already extended to every other plan field (Priority, Status, Scope, etc.). Matching between the plan's `Approval needed:` text and the policy's `Human approval required` bullets, or between the plan field and the recorded approval's category text, is not string-enforced — `has_approval()` only checks that *some* record exists for the task ID.
Alternatives considered: (a) Automatic keyword matching — scan the task's Goal/Scope/Notes text for words drawn from the policy's approval-required bullets and block on overlap. Rejected: heuristic, would produce real false positives (a task merely mentioning "network" in an unrelated sentence) and false negatives (vaguely worded tasks), and adds matching logic to maintain for uncertain benefit over the simpler self-declared field. (b) Interactive-confirmation-only with no persistent record (`--approve-human-review` flag, no audit trail). Rejected: breaks unattended/autonomous operation, which is a large part of what this tool is for, and leaves no auditable record of who approved what or why — contrary to the project's existing pattern of auditable Markdown artifacts (decisions, changelog, sessions, run reports). (c) Descope AUTO-050 entirely, leave the section advisory-only. Rejected: the section already exists in every project's policy file and reads as an enforceable guarantee; leaving it permanently decorative would repeat the exact "safety narrative vs. actual enforcement" gap DEC-012 was created to close, just for a harder category.
Consequences: A task's approval gate is only as strong as its author's honesty in setting `Approval needed:` — an agent or human writing a task that adds network access could simply omit the field and the gate never fires. This is a known, accepted limitation, not an oversight: the project's task-selection and plan-authoring model already trusts self-reported task metadata throughout (e.g. `Scope`, `Expected files or areas` are never verified against the actual diff either). `forge approve` has no authentication beyond "whoever can run the CLI" — appropriate for this tool's single-operator, trusted-repo scope, not appropriate to lift into a multi-operator context without further design.
Human decision still required: No for implementation — this decision itself is the human sign-off (mechanism confirmed with the user, including the exact field name, file location, and CLI command shape, before writing any code). Future extension (e.g. requiring the recorded approval's category text to exactly match the plan field, or adding automatic detection as a non-blocking advisory hint layered on top of the manual gate) would be a new decision, not an extension of this one.

## DEC-012 — 2026-07-25 — Make policy enforcement fail-closed (Roadmap v7)

Context: An external codebase assessment (`CODEBASE_ASSESSMENT.md`) found that policy enforcement is advisory rather than blocking in two ways, both independently verified against the actual code: (1) `commit.py`/`run.py` only skip policy diff-checking when the policy file is missing or unreadable — a missing/malformed policy does not block a commit, it just silently disables the check; (2) both `run.py` and `commit.py` only treat `rule == "prohibited"` violations as blocking — files outside the `Allowed paths` list ("not-allowed") are reported but never block, making the allowlist advisory. This exact gap was hit directly this session: `.forge/config.toml` and `.gitignore` showed "not-allowed" warnings on every commit until the allowlist was manually widened (DEC-011) — the tool never actually enforced the boundary itself.
Decision: Flip both to fail-closed by default, planned as Roadmap v7 (AUTO-048 and AUTO-049): a missing/malformed policy blocks mutating commands (`commit`, `pipeline --commit`, `mark`, `plan add`, `import-orphans`) unless an explicit, prominently named override flag is passed; `not-allowed` (outside-allowlist) violations become blocking alongside `prohibited` ones, with an explicit opt-out for advisory-only mode if a repo wants it.
Alternatives considered: (a) leave it advisory-with-visibility as an intentional design choice for a personal/trusted-repo tool — rejected because the project's own documentation and policy vocabulary ("Allowed paths", "Prohibited paths") already imply blocking semantics; the gap is between what's promised and what's enforced, not a deliberate trade-off; (b) fix only the missing-policy case and leave the allowlist advisory — rejected because both gaps stem from the same root problem (only `prohibited` truly blocks) and fixing one without the other leaves the safety narrative still overstated.
Consequences: Existing repos with an incomplete allowlist (including this one, historically) will start seeing blocked commits instead of warnings — expect friction until allowlists are kept current, which is the point. An explicit override flag preserves an escape hatch for legitimate cases without silently reintroducing the old advisory behavior as the default.
Human decision still required: No for implementation — this decision itself is the human sign-off (confirmed explicitly with the user before creating Roadmap v7's tasks). Follow-up: item 2 from the assessment (structured "Human approval required" enforcement, AUTO-050) is a separate, still-open design question not resolved by this decision.

## DEC-011 — 2026-07-24 — Add .forge/**, .gitignore, and pyproject.toml to the policy allowed paths

Context: AUTO-039 added `.forge/config.toml`. `forge commit`'s pre-flight flagged it as "not covered by any allowed path pattern" — a soft warning, not a block — because `.forge/policy.md`'s own allowed-paths list never included `.forge/**`. That gap predates AUTO-039: the policy file itself, `.forge/policy.md`, was never technically "allowed" by its own rules either. AUTO-040's commit (adding `.forge/.lock` to `.gitignore`) surfaced the same gap for `.gitignore` itself; checking further found `pyproject.toml` — routinely edited for version bumps or dependency changes — was never allowed either.
Decision: Add `.forge/**`, `.gitignore`, and `pyproject.toml` to the allowed paths in `.forge/policy.md`. `.forge/sessions/` and `.forge/runs/` are already gitignored and never reach a commit regardless, so `.forge/**` only practically affects committed files like `policy.md` and `config.toml`.
Alternatives considered: Leave it as a permanent soft warning (rejected — it would fire on every future commit touching these routine project files forever, training reviewers to ignore diff-check output); scope the allow-list narrowly to specific filenames instead of `.forge/**` (rejected for `.forge/` — needlessly brittle for a directory whose only other contents are already gitignored; not applicable to `.gitignore`/`pyproject.toml`, which are already exact filenames).
Consequences: `forge check`/`forge commit` pre-flight no longer flags legitimate commits to the project's own core metadata and packaging files. No safety regression — prohibited paths (`.env`, secrets, `.github/workflows/**`) are unaffected, and the gitignored `.forge/` subdirectories still never appear in a diff.
Human decision still required: No — policy allow-list additions for the project's own existing, routinely-edited files are ordinary maintenance, not the kind of prohibited-path or approval-category change requiring separate sign-off.

## DEC-010 — 2026-07-23 — Allow explicit, human-triggered Forgejo-to-plan import

Context: AUTO-035 (Roadmap v4) deliberately made orphan-issue detection read-only, with the stated principle that a human decides what, if anything, gets promoted from Forgejo into the plan, preserving "the plan is the source of truth." Roadmap v5 now wants a command that actually creates `AUTO-xxx` plan stubs from orphan Forgejo issues, which is a partial reversal of that stance.
Decision: Add `forge sync --import-orphans` as a new explicit, human-triggered command. Running it converts current orphan issues into `AUTO-xxx` plan stubs in the plan file in one shot — no per-issue interactive prompt — but the human still reviews the resulting plan diff and decides whether to commit it, same as any other plan edit. `forge sync --report-orphans` remains read-only and unchanged; import is strictly opt-in and separate.
Alternatives considered: (a) per-issue interactive confirmation before each stub is created — rejected as slower for the common case of importing several issues at once, with review happening at the diff/commit stage instead; (b) fully automatic import inside `forge run`/`forge pipeline` with no human trigger at all — rejected as too large a reversal of "human decides" for now.
Consequences: Closes a real workflow gap (issues filed in Forgejo that never make it into the plan) while keeping a human review point (the plan diff) before anything is considered real. The "plan is the source of truth" principle is preserved in spirit — Forgejo can now seed the plan, but only when a human explicitly asks for it and reviews the result.
Human decision still required: Yes — running the command is the trigger, and the resulting plan diff still needs human review before commit.

## DEC-009 — 2026-07-07 — Keep inventory limited to file-presence signals

Context: AUTO-013 documented a safe repository health inventory scope, and the next smallest coherent task was to expose that scope through the CLI.
Decision: Add `forge inventory` as a read-only file-presence summary over the documented paths only.
Alternatives considered: Add scoring, inspect file contents, inspect environment settings, enforce policy boundaries, or run validation commands.
Consequences: Maintainers get a quick local readiness view while the tool avoids broader audit, enforcement, scanning, or execution claims.
Human decision still required: No.

## DEC-008 — 2026-07-07 — Scope health inventory before implementation

Context: Roadmap v2 completed run-summary preview work, and the state file recommended adding the next smallest read-only task before implementing further behavior.
Decision: Document the first repository health inventory scope in `docs/HEALTH_INVENTORY.md` before adding any `forge inventory` command.
Alternatives considered: Implement the inventory command immediately, add scoring or audit language, or skip inventory work and move directly to run-summary persistence.
Consequences: Future inventory work has clear local-only, read-only boundaries and avoids implying enforcement, credential scanning, health scoring, or external command execution before those behaviors are explicitly approved.
Human decision still required: No.

## DEC-007 — 2026-07-07 — Preview run summaries before persistence

Context: AUTO-011 documented the local run-summary format, and the project still prohibits automatic execution-history writes.
Decision: Add `forge run-summary` as a read-only preview command that prints the documented fields without writing files, running validation, inspecting diffs, or creating commits.
Alternatives considered: Add automatic history persistence immediately, leave the format documentation-only, or fold preview output into `forge report`.
Consequences: Maintainers can inspect the future record shape with real plan and policy context while preserving the current read-only safety boundary.
Human decision still required: No.

## DEC-006 — 2026-07-07 — Define run summaries before writing them

Context: AUTO-011 introduces the local run-summary concept as part of durable repository memory, but the project does not yet allow automatic execution-history writes.
Decision: Define the run-summary fields and safety limits in `docs/RUN_SUMMARIES.md` before adding any preview or persistence command.
Alternatives considered: Add a writer immediately, add a read-only preview command in the same task, or leave the format implicit until later.
Consequences: Future implementation has a reviewable target format, while current behavior remains documentation-only and avoids premature write behavior.
Human decision still required: No.

## DEC-005 — 2026-07-07 — Document implemented command contracts only

Context: AUTO-010 adds command output contracts so maintainers, contributors, and future automation can understand current CLI behavior before more commands are added.
Decision: `docs/COMMANDS.md` documents only implemented read-only commands, their inputs, expected human-readable output patterns, exit-code expectations, and safety limits.
Alternatives considered: Document future commands early, add tests that snapshot every output line, or change CLI behavior while writing the contract.
Consequences: Contributors get clearer expectations without expanding product behavior, but the document must be updated whenever command behavior intentionally changes.
Human decision still required: No.

## DEC-004 — 2026-07-07 — Keep roadmap linting read-only and strict

Context: AUTO-009 adds structure checks for roadmap task blocks before any higher-risk automation is considered.
Decision: `forge lint-plan` will stay read-only and report diagnostics for malformed task headings, missing required task fields, unsupported priorities, and unsupported statuses without modifying the roadmap or selecting work.
Alternatives considered: Silently tolerate incomplete task blocks, auto-repair the roadmap, or merge linting into task selection only.
Consequences: Maintainers get clearer roadmap quality feedback while the command remains safe, predictable, and separate from task selection.
Human decision still required: No.

## DEC-003 — 2026-07-07 — Report policy readiness without enforcement

Context: AUTO-007 added conservative parsing for `.forge/policy.md`. AUTO-008 needed to make that safety boundary visible in `forge report` before any future autonomous behavior relies on policy information.
Decision: `forge report` will show policy readiness as present/readable, missing, or malformed, but it will not enforce path decisions or claim that policy enforcement exists.
Alternatives considered: Fail the whole report when policy is missing, silently ignore policy state, or implement path enforcement immediately.
Consequences: Maintainers get clearer safety readiness information while the tool remains read-only and honest about its current limits.
Human decision still required: No.

## DEC-002 — 2026-07-07 — Make policy inspection the Roadmap v2 foundation

Context: Roadmap v1 completed the local CLI, deterministic task parsing and selection, dry-run report, policy documentation, and contributor guidance. The repository now has documented policy boundaries but no code that can inspect them.
Decision: Roadmap v2 will begin with conservative, read-only parsing and reporting of `.forge/policy.md` before adding any higher-risk automation or write behavior.
Alternatives considered: Add a repository health scanner first, add external command execution, add GitHub issue import, or implement automatic file writes.
Consequences: Policy inspection strengthens safety and transparency before execution features, but it delays more visible automation features until the tool can explain repository boundaries clearly.
Human decision still required: No.

## DEC-001 — 2026-07-07 — Start with a Python CLI

Context: Roadmap v1 defines Autonomous Forge as a local-first developer tool that needs a stable command surface before planner behavior can be used.
Decision: Use a zero-runtime-dependency Python package with a `forge` console script as the initial implementation surface.
Alternatives considered: Shell-only scripts, a hosted service, or a JavaScript package.
Consequences: Python keeps the MVP small and testable, but packaging and CLI behavior must remain simple until the plan parser exists.
Human decision still required: No.
