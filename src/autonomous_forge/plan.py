"""Parse and select Autonomous Forge roadmap task blocks."""

from __future__ import annotations

from dataclasses import dataclass
import re


_TASK_HEADING_RE = re.compile(r"^### (AUTO-\d{3}) — (.+)$")
_FIELD_RE = re.compile(r"^([^:]+):\s*(.*)$")
_TASK_FIELD_RE = re.compile(r"^(Priority|Status):\s*(.+)$")
_PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
_SUPPORTED_STATUSES = {"TODO", "DONE", "BLOCKED", "SKIPPED"}
_REQUIRED_TASK_FIELDS = (
    "Priority",
    "Status",
    "Goal",
    "Why it matters",
    "Scope",
    "Expected files or areas",
    "Acceptance criteria",
    "Validation",
    "Risks or assumptions",
    "Notes",
)


@dataclass(frozen=True)
class PlanTask:
    """A task parsed from the autonomous roadmap."""

    task_id: str
    title: str
    priority: str
    status: str
    line_number: int


@dataclass(frozen=True)
class PlanLintDiagnostic:
    """A roadmap structure issue reported by the plan linter."""

    line_number: int
    message: str


class PlanParseError(ValueError):
    """Raised when a roadmap task block is malformed."""


class PlanSelectionError(ValueError):
    """Raised when a task cannot be selected from parsed roadmap data."""


def parse_plan_tasks(plan_text: str) -> list[PlanTask]:
    """Parse task headings, priorities, and statuses from roadmap Markdown."""
    lines = plan_text.splitlines()
    tasks: list[PlanTask] = []
    index = 0

    while index < len(lines):
        heading_match = _TASK_HEADING_RE.match(lines[index])
        if not heading_match:
            index += 1
            continue

        task_id, title = heading_match.groups()
        line_number = index + 1
        fields: dict[str, str] = {}
        index += 1

        while index < len(lines) and not lines[index].startswith("### "):
            field_match = _TASK_FIELD_RE.match(lines[index])
            if field_match:
                fields[field_match.group(1)] = field_match.group(2).strip()
            index += 1

        missing = [field for field in ("Priority", "Status") if field not in fields]
        if missing:
            missing_text = ", ".join(missing)
            raise PlanParseError(
                f"{task_id} at line {line_number} is missing required field(s): {missing_text}"
            )

        tasks.append(
            PlanTask(
                task_id=task_id,
                title=title.strip(),
                priority=fields["Priority"],
                status=fields["Status"],
                line_number=line_number,
            )
        )

    return tasks


def lint_plan_structure(plan_text: str) -> list[PlanLintDiagnostic]:
    """Return read-only diagnostics for roadmap task block structure."""
    lines = plan_text.splitlines()
    diagnostics: list[PlanLintDiagnostic] = []
    seen_task_ids: set[str] = set()
    index = 0

    while index < len(lines):
        if not lines[index].startswith("### "):
            index += 1
            continue

        heading_match = _TASK_HEADING_RE.match(lines[index])
        if not heading_match:
            diagnostics.append(
                PlanLintDiagnostic(
                    index + 1,
                    "Task heading must use '### AUTO-### — Title' format.",
                )
            )
            index += 1
            continue

        task_id, title = heading_match.groups()
        line_number = index + 1
        if task_id in seen_task_ids:
            diagnostics.append(
                PlanLintDiagnostic(line_number, f"Duplicate task id: {task_id}")
            )
        seen_task_ids.add(task_id)

        if not title.strip():
            diagnostics.append(
                PlanLintDiagnostic(line_number, f"{task_id} has an empty title.")
            )

        fields: dict[str, tuple[int, str]] = {}
        index += 1
        while index < len(lines) and not lines[index].startswith("### "):
            field_match = _FIELD_RE.match(lines[index])
            if field_match:
                field_name = field_match.group(1).strip()
                if field_name in _REQUIRED_TASK_FIELDS:
                    fields[field_name] = (index + 1, field_match.group(2).strip())
            index += 1

        for field_name in _REQUIRED_TASK_FIELDS:
            if field_name not in fields:
                diagnostics.append(
                    PlanLintDiagnostic(
                        line_number,
                        f"{task_id} is missing required field: {field_name}",
                    )
                )

        priority = fields.get("Priority")
        if priority and priority[1] not in _PRIORITY_ORDER:
            diagnostics.append(
                PlanLintDiagnostic(
                    priority[0],
                    f"{task_id} has unsupported priority: {priority[1]}",
                )
            )

        status = fields.get("Status")
        if status and status[1] not in _SUPPORTED_STATUSES:
            diagnostics.append(
                PlanLintDiagnostic(
                    status[0],
                    f"{task_id} has unsupported status: {status[1]}",
                )
            )

    return diagnostics


def select_eligible_task(tasks: list[PlanTask]) -> PlanTask | None:
    """Return the next TODO task by priority, preserving source order for ties."""
    eligible: list[tuple[int, int, PlanTask]] = []

    for source_index, task in enumerate(tasks):
        if task.status != "TODO":
            continue
        if task.priority not in _PRIORITY_ORDER:
            raise PlanSelectionError(
                f"{task.task_id} has unsupported priority: {task.priority}"
            )
        eligible.append((_PRIORITY_ORDER[task.priority], source_index, task))

    if not eligible:
        return None

    return min(eligible, key=lambda item: (item[0], item[1]))[2]
