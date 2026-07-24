"""Full autonomous pipeline: run -> commit -> sync in one command."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datetime import datetime, timezone

from autonomous_forge.commit import CommitResult, execute_commit, run_pre_flight
from autonomous_forge.lock import LockHeldError, acquire_lock
from autonomous_forge.push import PushResult, execute_push
from autonomous_forge.run import RunOutcome, execute_run, record_commit_hash, save_run_outcome
from autonomous_forge.sync import SyncResult, execute_sync


@dataclass(frozen=True)
class PipelineResult:
    """Complete result of a full pipeline execution."""

    run_outcome: RunOutcome | None
    commit_result: CommitResult | None
    push_result: PushResult | None
    sync_result: SyncResult | None
    stage_reached: str  # "run", "commit", "push", "sync", "complete"
    stopped_reason: str


def execute_pipeline(
    root: Path = Path("."),
    plan_path: Path | None = None,
    policy_path: Path | None = None,
    validate_command: str | None = None,
    commit: bool = False,
    push: bool = False,
    sync: bool = False,
    commit_message: str | None = None,
    dry_run: bool = False,
    timestamp: str | None = None,
) -> PipelineResult:
    """Execute the full forge pipeline: run -> commit -> push -> sync.

    Holds the `.forge/.lock` guard (see `autonomous_forge.lock`) for the
    entire pipeline, not just the run stage — the internal `execute_run`
    call is made with locking disabled since this function already holds it.
    """
    ts = timestamp or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    try:
        lock = acquire_lock(root, timestamp=ts)
    except LockHeldError as exc:
        blocked_outcome = RunOutcome(
            timestamp=ts,
            selected_task=None,
            validation_passed=None,
            validation_command="",
            validation_output="",
            diff_violations=0,
            diff_details=(),
            drift_signals=0,
            changed_files=(),
            policy_status="unknown",
            blocked=True,
            block_reason=str(exc),
        )
        return PipelineResult(
            run_outcome=blocked_outcome,
            commit_result=None,
            push_result=None,
            sync_result=None,
            stage_reached="run",
            stopped_reason=f"Blocked: {blocked_outcome.block_reason}",
        )

    try:
        return _execute_pipeline_body(
            root, plan_path, policy_path, validate_command,
            commit, push, sync, commit_message, dry_run, ts,
        )
    finally:
        lock.release()


def _execute_pipeline_body(
    root: Path,
    plan_path: Path | None,
    policy_path: Path | None,
    validate_command: str | None,
    commit: bool,
    push: bool,
    sync: bool,
    commit_message: str | None,
    dry_run: bool,
    timestamp: str,
) -> PipelineResult:
    """Run each pipeline stage in sequence (no locking — caller holds it)."""
    run_outcome = execute_run(
        root,
        plan_path=plan_path,
        policy_path=policy_path,
        validate_command=validate_command,
        dry_run=dry_run,
        timestamp=timestamp,
        use_lock=False,
    )
    run_report_path = save_run_outcome(run_outcome, root)

    if run_outcome.blocked:
        return PipelineResult(
            run_outcome=run_outcome,
            commit_result=None,
            push_result=None,
            sync_result=None,
            stage_reached="run",
            stopped_reason=f"Blocked: {run_outcome.block_reason}",
        )

    if run_outcome.selected_task is None:
        return PipelineResult(
            run_outcome=run_outcome,
            commit_result=None,
            push_result=None,
            sync_result=None,
            stage_reached="run",
            stopped_reason="No TODO tasks — nothing to do.",
        )

    if run_outcome.validation_passed is False:
        return PipelineResult(
            run_outcome=run_outcome,
            commit_result=None,
            push_result=None,
            sync_result=None,
            stage_reached="run",
            stopped_reason="Validation failed — not safe to commit.",
        )

    if not commit:
        return PipelineResult(
            run_outcome=run_outcome,
            commit_result=None,
            push_result=None,
            sync_result=None,
            stage_reached="run",
            stopped_reason="Commit not requested (use --commit to auto-commit).",
        )

    commit_result = execute_commit(
        root,
        message=commit_message,
        plan_path=plan_path,
        policy_path=policy_path,
        validate=False,  # already validated in the run stage
        staged_only=True,
    )

    if not commit_result.committed:
        return PipelineResult(
            run_outcome=run_outcome,
            commit_result=commit_result,
            push_result=None,
            sync_result=None,
            stage_reached="commit",
            stopped_reason=f"Commit failed: {commit_result.message}",
        )

    record_commit_hash(run_report_path, commit_result.commit_hash)

    if not push:
        return PipelineResult(
            run_outcome=run_outcome,
            commit_result=commit_result,
            push_result=None,
            sync_result=None,
            stage_reached="commit",
            stopped_reason="Push not requested (use --push to push commits to the git remote).",
        )

    push_result = execute_push(root)

    if not push_result.pushed:
        return PipelineResult(
            run_outcome=run_outcome,
            commit_result=commit_result,
            push_result=push_result,
            sync_result=None,
            stage_reached="push",
            stopped_reason=f"Push failed: {push_result.message}",
        )

    if not sync:
        return PipelineResult(
            run_outcome=run_outcome,
            commit_result=commit_result,
            push_result=push_result,
            sync_result=None,
            stage_reached="push",
            stopped_reason="Sync not requested (use --sync to sync Forgejo issue status).",
        )

    sync_result = execute_sync(
        root,
        plan_path=plan_path,
        dry_run=dry_run,
    )

    return PipelineResult(
        run_outcome=run_outcome,
        commit_result=commit_result,
        push_result=push_result,
        sync_result=sync_result,
        stage_reached="complete",
        stopped_reason="" if not sync_result.errors else f"Sync errors: {sync_result.errors[0]}",
    )


def format_pipeline_result(result: PipelineResult) -> str:
    """Format a pipeline result as a concise report."""
    lines = ["Forge pipeline"]

    if result.run_outcome:
        ro = result.run_outcome
        if ro.selected_task:
            lines.append(f"Task: {ro.selected_task.task_id} — {ro.selected_task.title}")
        else:
            lines.append("Task: none")

        lines.append(f"Changed files: {len(ro.changed_files)}")
        lines.append(f"Drift: {ro.drift_signals}")
        lines.append(f"Violations: {ro.diff_violations}")

        if ro.validation_passed is not None:
            lines.append(f"Validation: {'PASSED' if ro.validation_passed else 'FAILED'}")

    stages = []
    if result.run_outcome:
        stages.append("run")
    if result.commit_result and result.commit_result.committed:
        stages.append(f"commit ({result.commit_result.commit_hash})")
    if result.push_result and result.push_result.pushed:
        stages.append(f"push ({result.push_result.commits_pushed} commit(s))")
    if result.sync_result:
        created = sum(1 for a in result.sync_result.actions if a.action == "created")
        updated = sum(1 for a in result.sync_result.actions if a.action not in ("created", "up-to-date", "error"))
        stages.append(f"sync ({created} created, {updated} updated)")

    lines.append(f"Stages: {' -> '.join(stages)}")

    if result.stopped_reason:
        lines.append(f"Stopped: {result.stopped_reason}")
    else:
        lines.append("Result: pipeline complete")

    return "\n".join(lines)
