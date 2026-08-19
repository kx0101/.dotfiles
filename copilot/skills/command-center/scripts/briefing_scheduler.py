#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from briefing_contract import build_daily_briefing, render_markdown


ROOT = Path(__file__).resolve().parent
COMMAND = ROOT / "command_center.py"
NOTIFIER = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Command Center"
    / "CommandCenterNotifier.app"
    / "Contents"
    / "MacOS"
    / "CommandCenterNotifier"
)
NOTIFIER_APP = NOTIFIER.parents[2]
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
    unique: list[dict] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for item in items:
        item_title = task_title(item)
        key = (item_title.casefold(), tuple(item.get(field, "") for field in fields))
        if key not in seen:
            seen.add(key)
            unique.append(item)
    items = unique
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


def event_line(event: dict) -> str:
    if event.get("all_day") == "true":
        time_label = "Ολοήμερο"
    else:
        try:
            time_label = datetime.fromisoformat(event["start"]).astimezone().strftime("%H:%M")
        except (KeyError, ValueError):
            time_label = event.get("start", "")
    title = event.get("title", "")
    calendar = event.get("calendar", "")
    source = " ".join(
        value for value in (event.get("url", ""), event.get("description", ""))
        if value
    )
    join = re.search(
        r"https://(?:meet\.google\.com|[^/\s]+\.zoom\.us|"
        r"teams\.microsoft\.com|teams\.live\.com)/[^\s<>\"]+",
        source,
        re.IGNORECASE,
    )
    link = f" · Join: {join.group(0)}" if join else ""
    return f"- {time_label} · {title} [{calendar}]{link}"


def render_agenda(events: list[dict]) -> list[str]:
    lines = ["## Agenda σήμερα (ώρα Ελλάδας)"]
    if not events:
        return lines + ["- Κανένα."]
    lines.extend(event_line(event) for event in events)
    return lines


def render_morning() -> str:
    selected_date = datetime.now().astimezone().date().isoformat()
    run_command("daily-rollover", "--date", selected_date)
    daily = run_command("daily-tasks", "--include-completed")
    calendar = run_command("calendar-today")["events"]
    overdue = run_command("task-list", "--view", "overdue")["tasks"]
    reminders = [event for event in calendar if event.get("kind") == "reminder"]
    contract = build_daily_briefing(
        selected_date=selected_date,
        personal=daily["personal"],
        work=daily["work"],
        agenda=calendar,
        reminders=reminders,
        overdue=overdue,
    )
    return render_markdown(
        contract,
        f"# Morning briefing — {selected_date}",
    )


def render_weekly() -> str:
    run_command("daily-rollover", "--date", datetime.now().astimezone().date().isoformat())
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
    lines += render_agenda(calendar["events"])
    return "\n".join(lines) + "\n"


def notify(kind: str, path: Path, content: str) -> None:
    preview = [
        line.removeprefix("- ").strip()
        for line in content.splitlines()
        if line.startswith("- ")
    ][:4]
    message = f"{kind} briefing έτοιμο"
    if preview:
        message += " · " + " · ".join(preview)
    subprocess.run([str(NOTIFIER), kind, str(path), message], check=True)
    subprocess.Popen(
        [
            "open",
            "-n",
            str(NOTIFIER_APP),
            "--args",
            "--show",
            str(path),
        ],
        start_new_session=True,
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
    notify(kind, path, content)
    print(path)


if __name__ == "__main__":
    main()
