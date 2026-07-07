"""Parse Autonomous Forge roadmap task blocks."""

from __future__ import annotations

from dataclasses import dataclass
import re


_TASK_HEADING_RE = re.compile(r"^### (AUTO-\d{3}) — (.+)$")
_FIELD_RE = re.compile(r"^(Priority|Status):\s*(.+)$")


@dataclass(frozen=True)
class PlanTask:
    """A task parsed from the autonomous roadmap."""

    task_id: str
    title: str
    priority: str
    status: str
    line_number: int


class PlanParseError(ValueError):
    """Raised when a roadmap task block is malformed."""


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
            field_match = _FIELD_RE.match(lines[index])
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
