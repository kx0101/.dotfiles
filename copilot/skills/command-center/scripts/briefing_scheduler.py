#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
COMMAND = ROOT / "command_center.py"
ARCHIVE = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Command Center"
    / "Briefings"
)


def run_command(*arguments: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(COMMAND), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def task_title(task: dict) -> str:
    value = task.get("title") or task.get("item") or ""
    if isinstance(value, dict):
        value = (
            value.get("title")
            or value.get("item")
            or value.get("display_name")
            or value.get("subject")
            or value
        )
    return str(value).strip()


def render_items(title: str, items: list[dict], fields: tuple[str, ...] = ()) -> list[str]:
    lines = [f"## {title}"]
    if not items:
        return lines + ["- Κανένα."]
    for item in items:
        suffix = " · ".join(
            str(item[field])
            for field in fields
            if item.get(field)
        )
        lines.append(f"- {task_title(item)}" + (f" ({suffix})" if suffix else ""))
    return lines


def render_morning() -> str:
    home = run_command("home", "--include-personal", "--include-work")
    exceptions = run_command("exceptions")
    morning = home["morning"]
    lines = [
        f"# Morning briefing — {datetime.now().astimezone():%Y-%m-%d}",
        "",
        f"Exceptions: {exceptions['summary']['total']} "
        f"(critical {exceptions['summary']['critical']}, "
        f"warning {exceptions['summary']['warning']})",
        "",
    ]
    lines += render_items(
        "Επείγοντα σήμερα",
        exceptions["exceptions"],
    )
    lines += render_items("Εκπρόθεσμα tasks", morning["tasks"])
    lines += render_items(
        "Personal σήμερα",
        home["daily_tasks"].get("personal", []),
    )
    lines += render_items(
        "Work σήμερα",
        home["daily_tasks"].get("work", []),
    )
    calendar = morning.get("calendar") or []
    timed = [event for event in calendar if event.get("all_day") == "false"]
    reminders = [event for event in calendar if event.get("kind") == "reminder"]
    all_day = [
        event
        for event in calendar
        if event.get("all_day") == "true" and event not in reminders
    ]
    lines += render_items("Calls και meetings", timed, ("start", "calendar"))
    lines += render_items("Reminders και todos", reminders, ("start", "calendar"))
    lines += render_items("Holidays, birthdays και notes", all_day, ("calendar",))
    if morning.get("errors"):
        lines += ["", "## Integrations με σφάλμα"]
        lines.extend(f"- {name}: {message}" for name, message in morning["errors"].items())
    return "\n".join(lines) + "\n"


def render_weekly() -> str:
    review = run_command("weekly-review")
    exceptions = run_command("exceptions")
    calendar = run_command("calendar-today")
    lines = [
        f"# Weekly briefing — {datetime.now().astimezone():%Y-%m-%d}",
        "",
        f"Εκκρεμότητες: {len(review['tasks'])}",
        f"Inbox: {review['inbox_count']}",
        f"Learning pending: {review['learning_pending']}",
        f"Exceptions: {exceptions['summary']['total']}",
        "",
    ]
    lines += render_items("Tasks για review", review["tasks"])
    lines += render_items(
        "Work πρόσφατα εκπρόθεσμα",
        review["work"]["recent_overdue"],
    )
    lines += ["", "## Project records"]
    lines.extend(
        f"- {project}: {count} ενεργές καταγραφές"
        for project, count in review["project_records"].items()
    ) or lines.append("- Κανένα.")
    health_failures = [
        check for check in review["health"] if not check.get("up")
    ]
    lines += render_items("Health failures", health_failures, ("project", "error"))
    lines += ["", "## Σήμερα"]
    lines += render_items(
        "Calls και meetings",
        [event for event in calendar["events"] if event.get("all_day") == "false"],
        ("start", "calendar"),
    )
    lines += render_items(
        "Reminders και todos",
        [event for event in calendar["events"] if event.get("kind") == "reminder"],
        ("start", "calendar"),
    )
    return "\n".join(lines) + "\n"


def notify(kind: str, path: Path) -> None:
    title = "Command Center"
    message = f"{kind} briefing έτοιμο"
    subprocess.run(
        [
            "osascript",
            "-e",
            f'display notification "{message}" with title "{title}"',
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"morning", "weekly"}:
        raise SystemExit("Usage: briefing_scheduler.py morning|weekly")
    kind = sys.argv[1]
    content = render_morning() if kind == "morning" else render_weekly()
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    path = ARCHIVE / f"{kind}-{datetime.now().astimezone():%Y-%m-%d}.md"
    path.write_text(content, encoding="utf-8")
    notify(kind, path)
    print(path)


if __name__ == "__main__":
    main()
