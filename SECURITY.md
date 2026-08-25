# Security and threat model

Autonomous Forge is a **local, single-operator workflow tool**, not a sandbox and not an authentication system. This document states its trust model plainly so nobody mistakes a design tradeoff for a safety guarantee the tool doesn't actually make.

## Who this is for

Autonomous Forge is built for one trusted operator (a human, or an agent acting on that human's behalf) working in a repository and branch they already trust. It is not designed, and should not be used, as an isolation boundary between untrusted code and your machine, credentials, or environment.

## Validation runs full local code execution — it is not a sandbox

`forge run`, `forge check`, `forge commit`, `forge pipeline`, and `forge watch` all invoke a validation command (`python -m pytest` by default, or whatever `.forge/policy.md` configures) as a subprocess that inherits your full process environment. The default test-runner invocation executes arbitrary repository Python code, same as running `pytest` yourself.

**Only run Autonomous Forge against repositories and branches whose code — and whose configured validation command — you trust.** A malicious repository or branch can read your credentials, modify files outside the repo, reach the network, or otherwise act with your full local privileges when validation runs. The shell-metacharacter scanner added in AUTO-051 reduces *accidental* shell interpretation of a validation command; it is not a security boundary against a validation command (or the code it runs) that is deliberately malicious.

There is no isolated/containerized execution mode today. If one is added in the future, this document will be updated — until then, do not assume isolation exists.

## "Human approval required" is a self-declared attestation, not authentication

`.forge/policy.md`'s `Human approval required` section, and a task's optional `Approval needed:` field, describe a convention: whoever authors a task can flag it as needing approval, and `forge approve` records that approval in a git-tracked file (`.forge/approvals.md`).

This is **an auditable operator attestation, not authenticated human approval**:

- `has_approval()` checks that *some* record exists for the task ID — it does not verify the recorded category matches the task's declared `Approval needed:` text, and it does not verify who ran `forge approve`.
- Anything able to edit the repository or invoke the `forge` CLI (a human, a script, an agent) can create an approval record. There is no identity or credential check.
- A risky change can also simply omit the `Approval needed:` field on its task, and the gate never fires at all — detection is entirely self-reported, the same trust model already extended to every other plan field (`Scope`, `Expected files or areas`, `Priority`, etc.).

Treat an approval record as evidence that *someone* asserted a category was reviewed, not as proof that a qualified human actually reviewed it.

## Task-to-diff attribution is conventional, not verified

A commit's `AUTO-###` label reflects task *selection* logic (highest-priority eligible TODO task), not a verified claim that the staged diff actually implements that task. `forge commit` reports a non-blocking advisory warning (see `docs/COMMANDS.md`'s `forge commit` section) when staged files don't match a task's declared `Expected files or areas`, but this never blocks a commit — see `.ai/DECISIONS.md` DEC-016 for why.

## Other things worth knowing

- **Validation output persisted to `.forge/runs/` is best-effort redacted, not guaranteed clean (AUTO-066).** `forge run`/`forge pipeline` pass captured stdout/stderr through pattern-based redaction (known provider key formats like `sk-ant-...`/`ghp_...`/`AKIA...`, generic `key=`/`token=`/`password=` assignments, and the exact value of any environment variable whose name looks secret-like) before writing the run summary. This catches common, recognizable shapes — it is **not** complete secret detection; arbitrary program output can still leak a credential in a shape no pattern here recognizes. Run files are also restricted to owner-only permissions where the platform supports it (POSIX; a no-op on Windows). Pass `--no-persist-output` to `forge run`/`forge pipeline` to omit the raw output block from the saved file entirely while still recording the run's pass/fail outcome.
- **Forgejo sync makes real API calls** to whatever instance is configured, using a token you provide. `forge sync --report-orphans`/`--import-orphans` are read-only against Forgejo; the default mode creates and updates issues, labels, and milestones.
- **`.forge/policy.md` is advisory-with-teeth, not a sandbox boundary.** It gates what `forge commit`/`forge check`/`forge pipeline` will *commit*, but has no effect on what the validation command itself can do while it runs (see the first section above).

## Reporting a security issue

This is a pre-1.0, actively developed project. If you find an issue that isn't already covered by the tradeoffs described above, please open an issue describing the concern — there is no dedicated security contact or disclosure process yet.
