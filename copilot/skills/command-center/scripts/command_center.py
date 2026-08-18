#!/usr/bin/env python3

from __future__ import annotations

import argparse
import fcntl
import hashlib
import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


TASKS_RELATIVE_PATH = Path("Command Center/Tasks.md")
PERSONAL_DAILY_RELATIVE_PATH = Path("Command Center/Daily Tasks")
PROJECTS_RELATIVE_PATH = Path("Command Center/Projects")
INBOX_RELATIVE_PATH = Path("Command Center/Inbox.md")
WAITING_ON_RELATIVE_PATH = Path("Command Center/Waiting-on.md")
LEARNING_RELATIVE_PATH = Path("Command Center/Learning.md")
WORK_RELATIVE_PATH = Path("Work")
AUDIT_PATH = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Command Center"
    / "audit.jsonl"
)
TASK_PATTERN = re.compile(r"^- \[(?P<state>[ xX])\] (?P<body>.+)$")
ACTION_DATE_PATTERN = re.compile(r"\s+📅\s+(?P<date>\d{4}-\d{2}-\d{2})")
COMPLETED_DATE_PATTERN = re.compile(r"\s+✅\s+(?P<date>\d{4}-\d{2}-\d{2})")
CALENDAR_METADATA_PATTERN = re.compile(
    r"\s+<!-- calendar: (?P<metadata>\{.*\}) -->$"
)
HEADING_PATTERN = re.compile(r"^##\s+(?P<name>.+?)\s*$")
RECORD_HEADING_PATTERN = re.compile(
    r"^###\s+(?P<timestamp>.+?)\s+·\s+(?P<label>.+?)\s*$"
)
RECORD_ID_PATTERN = re.compile(r"^<!-- id: (?P<id>[^ ]+) -->$")
RECORD_TIMESTAMP_PATTERN = re.compile(
    r"^<!-- timestamp: (?P<timestamp>[^ ]+) -->$"
)
SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)\b(password|passwd|api[_ -]?key|token|secret|connection[_ -]?string)"
    r"\b.{0,16}(?:[:=]|\bis\b|\bcontains\b|\bείναι\b|\beinai\b)\s*[\"']?\S{8,}"
)
SENSITIVE_SHAPE_PATTERN = re.compile(
    r"(?i)(?:"
    r"[?&](?:api[_-]?key|access[_-]?token|auth|key|secret|signature|token)="
    r"|authorization:\s*(?:bearer\s+)?"
    r"|sk_(?:live|test)_[A-Za-z0-9]+"
    r"|gh[pousr]_[A-Za-z0-9]+"
    r"|github_pat_[A-Za-z0-9_]+"
    r"|xox[a-z]-[A-Za-z0-9-]+"
    r"|AKIA[A-Z0-9]{16}"
    r"|AIza[A-Za-z0-9_-]{20,}"
    r")"
)
ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
EMAIL_PATTERN = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)
RECORD_KIND_LABELS = {
    "requirement": "Απαίτηση",
    "fact": "Πληροφορία",
    "idea": "Ιδέα",
    "decision": "Απόφαση",
    "note": "Σημείωση",
    "summary": "Ενημέρωση σύνοψης",
    "archive": "Αρχειοθέτηση",
}
RECORD_LABEL_KINDS = {label: kind for kind, label in RECORD_KIND_LABELS.items()}
LEARNING_KINDS = {
    "book": "Βιβλία",
    "article": "Άρθρα",
    "video": "Βίντεο",
    "course": "Μαθήματα",
    "resource": "Πόροι",
}
LEARNING_ITEM_PATTERN = re.compile(
    r"^- \[(?P<state>[ xX])\] (?P<title>.*?) "
    r"<!-- cc: (?P<metadata>\{.*\}) -->$"
)
WAITING_ITEM_PATTERN = re.compile(
    r"^- \[(?P<state>[ xX])\] (?P<person>.+?) — (?P<item>.+?) "
    r"<!-- cc: (?P<metadata>\{.*\}) -->$"
)
WORK_TASK_PATTERN = re.compile(
    r"^(?P<prefix>\s*(?:\d+\.|-)\s+)\[(?P<state>[ xX])\]\s+(?P<title>.+)$"
)
DAILY_TASK_PATTERN = re.compile(
    r"^(?P<prefix>\s*(?:\d+\.|-)\s+)\[(?P<state>[ xX])\]\s+(?P<title>.+)$"
)
MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


class CommandCenterError(Exception):
    pass


class IntegrationError(CommandCenterError):
    pass


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        fail(
            message,
            details={"usage": self.format_usage().strip()},
            exit_code=2,
        )


@dataclass
class Task:
    title: str
    section: str
    completed: bool
    action_date: str | None
    completed_date: str | None
    sync_provider: str | None
    calendar_name: str | None
    calendar_uid: str | None
    line_number: int
    relation: str


@dataclass
class Project:
    name: str
    area: str
    status: str
    lifecycle: str
    local_path: str | None
    github: str | None
    render_services: list[str]
    render_service_ids: list[str]
    resend_domains: list[str]
    source_paths: list[str]
    health_checks: list[str]
    note_path: str


@dataclass
class ProjectRecord:
    id: str
    timestamp: str
    kind: str
    text: str
    source: str
    supersedes: str | None
    active: bool


@dataclass
class LearningItem:
    id: str
    title: str
    kind: str
    url: str | None
    project: str | None
    source: str
    added: str
    completed: bool
    line_number: int


@dataclass
class WaitingOnItem:
    id: str
    person: str
    item: str
    due_date: str | None
    completed: bool
    line_number: int


@dataclass
class WorkTask:
    title: str
    parent_path: list[str]
    task_date: str
    path: str
    line_number: int
    completed: bool
    managed: bool
    sync_provider: str | None
    calendar_name: str | None
    calendar_uid: str | None


def emit(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def fail(message: str, *, details: Any = None, exit_code: int = 2) -> None:
    payload: dict[str, Any] = {"error": message}
    if details is not None:
        payload["details"] = details
    print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
    raise SystemExit(exit_code)


def discover_vault(explicit: str | None) -> Path:
    if explicit:
        vault = Path(explicit).expanduser()
    elif os.environ.get("COMMAND_CENTER_VAULT"):
        vault = Path(os.environ["COMMAND_CENTER_VAULT"]).expanduser()
    else:
        config = (
            Path.home()
            / "Library"
            / "Application Support"
            / "obsidian"
            / "obsidian.json"
        )
        vault = _vault_from_obsidian_config(config)

    vault = vault.resolve()
    if not vault.is_dir():
        raise CommandCenterError(f"Obsidian vault does not exist: {vault}")
    return vault


def _vault_from_obsidian_config(config: Path) -> Path:
    if config.is_file():
        try:
            data = json.loads(config.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandCenterError(
                f"Cannot read Obsidian vault configuration: {config}"
            ) from exc

        vaults = list(data.get("vaults", {}).values())
        if vaults:
            active = [vault for vault in vaults if vault.get("open")]
            selected = max(active or vaults, key=lambda vault: vault.get("ts", 0))
            path = selected.get("path")
            if path:
                return Path(path).expanduser()

    fallback = Path.home() / "Documents" / "vault"
    if fallback.is_dir():
        return fallback
    raise CommandCenterError(
        "Cannot discover an Obsidian vault. Pass --vault or set COMMAND_CENTER_VAULT."
    )


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


@contextmanager
def path_lock(path: Path):
    digest = hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()
    locks_dir = Path.home() / ".cache" / "command-center" / "locks"
    locks_dir.mkdir(parents=True, exist_ok=True)
    lock_path = locks_dir / f"{digest}.lock"
    with lock_path.open("a", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def audit_event(
    action: str,
    entity: str,
    title: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_title = " ".join(title.split())
    values = [action, entity, normalized_title, json.dumps(details or {})]
    if any(
        SENSITIVE_VALUE_PATTERN.search(value)
        or SENSITIVE_SHAPE_PATTERN.search(value)
        for value in values
    ):
        raise CommandCenterError("Audit event contains credential-like data.")
    event = {
        "id": uuid.uuid4().hex,
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": os.environ.get("COMMAND_CENTER_SOURCE", "cli"),
        "action": action,
        "entity": entity,
        "title": normalized_title,
        "details": details or {},
    }
    with path_lock(AUDIT_PATH):
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_PATH.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def audit_list(limit: int) -> list[dict[str, Any]]:
    if limit < 1 or limit > 500:
        raise CommandCenterError("Audit limit must be between 1 and 500.")
    if not AUDIT_PATH.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        AUDIT_PATH.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CommandCenterError(
                f"Malformed audit event on line {line_number}."
            ) from exc
        events.append(event)
    return list(reversed(events[-limit:]))


def validate_iso_date(value: str) -> str:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise CommandCenterError(f"Invalid date '{value}'. Use YYYY-MM-DD.") from exc
    return value


def task_relation(action_date: str | None, completed: bool) -> str:
    if completed:
        return "completed"
    if action_date is None:
        return "inbox"
    parsed = date.fromisoformat(action_date)
    today = date.today()
    if parsed < today:
        return "overdue"
    if parsed == today:
        return "today"
    if parsed <= today + timedelta(days=7):
        return "week"
    return "future"


def reconcile_next_day(vault: Path, task_date: str | None) -> None:
    if not task_date:
        return
    next_date = date.fromisoformat(task_date) + timedelta(days=1)
    daily_rollover(vault, next_date.isoformat())


def parse_tasks(tasks_path: Path) -> list[Task]:
    if not tasks_path.is_file():
        raise CommandCenterError(f"Tasks file does not exist: {tasks_path}")

    tasks: list[Task] = []
    section = "Inbox"
    for index, line in enumerate(tasks_path.read_text(encoding="utf-8").splitlines()):
        heading = HEADING_PATTERN.match(line)
        if heading:
            section = heading.group("name")
            continue

        match = TASK_PATTERN.match(line)
        if not match:
            continue

        body = match.group("body")
        action_match = ACTION_DATE_PATTERN.search(body)
        completed_match = COMPLETED_DATE_PATTERN.search(body)
        calendar_match = CALENDAR_METADATA_PATTERN.search(body)
        action_date = action_match.group("date") if action_match else None
        completed_date = completed_match.group("date") if completed_match else None
        calendar_metadata = (
            json.loads(calendar_match.group("metadata"))
            if calendar_match
            else {}
        )
        title = ACTION_DATE_PATTERN.sub("", body)
        title = COMPLETED_DATE_PATTERN.sub("", title).strip()
        title = CALENDAR_METADATA_PATTERN.sub("", title).strip()
        completed = match.group("state").lower() == "x"
        tasks.append(
            Task(
                title=title,
                section=section,
                completed=completed,
                action_date=action_date,
                completed_date=completed_date,
                sync_provider=calendar_metadata.get("provider", "calendar")
                if calendar_metadata
                else None,
                calendar_name=calendar_metadata.get("name"),
                calendar_uid=calendar_metadata.get("uid"),
                line_number=index + 1,
                relation=task_relation(action_date, completed),
            )
        )
    return tasks


def parse_frontmatter(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise CommandCenterError(f"Project note has no frontmatter: {path}")

    result: dict[str, Any] = {}
    current_list: str | None = None
    for line in lines[1:]:
        if line == "---":
            break
        if current_list and line.startswith("  - "):
            result[current_list].append(_unquote(line[4:].strip()))
            continue

        current_list = None
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not raw_value:
            result[key] = []
            current_list = key
        else:
            result[key] = _unquote(raw_value)
    return result


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def load_projects(vault: Path) -> list[Project]:
    projects_dir = vault / PROJECTS_RELATIVE_PATH
    if not projects_dir.is_dir():
        return []

    projects: list[Project] = []
    for note in sorted(projects_dir.glob("*.md")):
        data = parse_frontmatter(note)
        projects.append(
            Project(
                name=str(data.get("name") or note.stem),
                area=str(data.get("area") or "personal").lower(),
                status=str(data.get("status") or "active").lower(),
                lifecycle=str(data.get("lifecycle") or "active").lower(),
                local_path=data.get("local_path") or None,
                github=data.get("github") or None,
                render_services=list(data.get("render_services") or []),
                render_service_ids=list(data.get("render_service_ids") or []),
                resend_domains=list(data.get("resend_domains") or []),
                source_paths=list(data.get("source_paths") or []),
                health_checks=list(data.get("health_checks") or []),
                note_path=str(note.relative_to(vault)),
            )
        )
    return projects


def project_by_name(vault: Path, name: str) -> Project:
    matches = [
        project
        for project in load_projects(vault)
        if project.name.casefold() == name.casefold()
    ]
    if not matches:
        raise CommandCenterError(f"Unknown project: {name}")
    return matches[0]


def sections_for_filter(vault: Path, requested: str | None) -> set[str] | None:
    if requested is None:
        return None
    lowered = requested.casefold()
    if lowered in {"personal", "work"}:
        sections = {lowered}
        sections.update(
            project.name.casefold()
            for project in load_projects(vault)
            if project.area == lowered and project.status == "active"
        )
        return sections
    project = project_by_name(vault, requested)
    return {project.name.casefold()}


def list_tasks(vault: Path, view: str, project: str | None) -> list[dict[str, Any]]:
    tasks = parse_tasks(vault / TASKS_RELATIVE_PATH)
    sections = sections_for_filter(vault, project)
    candidates = [
        task
        for task in tasks
        if not task.completed
        and (sections is None or task.section.casefold() in sections)
    ]

    allowed_relations = {
        "action": {"overdue", "today", "inbox"},
        "today": {"today"},
        "overdue": {"overdue"},
        "inbox": {"inbox"},
        "week": {"today", "week"},
        "all": {"overdue", "today", "inbox", "week", "future"},
    }[view]
    filtered = [
        task for task in candidates if task.relation in allowed_relations
    ]
    relation_order = {
        "overdue": 0,
        "today": 1,
        "inbox": 2,
        "week": 3,
        "future": 4,
    }
    filtered.sort(
        key=lambda task: (
            relation_order[task.relation],
            task.action_date or "9999-12-31",
            task.section.casefold(),
            task.title.casefold(),
        )
    )
    return [asdict(task) for task in filtered]


def ensure_tasks_file(vault: Path) -> Path:
    tasks_path = vault / TASKS_RELATIVE_PATH
    if not tasks_path.exists():
        atomic_write(
            tasks_path,
            "# Tasks\n\n## Inbox\n\n## Personal\n\n## Work\n",
        )
    return tasks_path


def ensure_task_section(tasks_path: Path, section: str) -> None:
    lines = tasks_path.read_text(encoding="utf-8").splitlines()
    if any(
        heading
        and heading.group("name").casefold() == section.casefold()
        for line in lines
        if (heading := HEADING_PATTERN.match(line))
    ):
        return
    content = tasks_path.read_text(encoding="utf-8").rstrip()
    atomic_write(tasks_path, f"{content}\n\n## {section}\n")


def append_task(tasks_path: Path, section: str, task_line: str) -> None:
    lines = tasks_path.read_text(encoding="utf-8").splitlines()
    section_index: int | None = None
    insert_index = len(lines)
    for index, line in enumerate(lines):
        heading = HEADING_PATTERN.match(line)
        if not heading:
            continue
        if heading.group("name").casefold() == section.casefold():
            section_index = index
            continue
        if section_index is not None:
            insert_index = index
            break

    if section_index is None:
        raise CommandCenterError(f"Task section does not exist: {section}")
    while insert_index > section_index + 1 and not lines[insert_index - 1].strip():
        insert_index -= 1
    lines.insert(insert_index, task_line)
    atomic_write(tasks_path, "\n".join(lines).rstrip() + "\n")


def append_line_to_section(content: str, section: str, line: str) -> str:
    lines = content.splitlines()
    bounds = markdown_section_bounds(lines, section)
    if bounds is None:
        return content.rstrip() + f"\n\n## {section}\n\n{line}\n"
    start, end = bounds
    insert_at = end
    while insert_at > start + 1 and not lines[insert_at - 1].strip():
        insert_at -= 1
    lines.insert(insert_at, line)
    return "\n".join(lines).rstrip() + "\n"


def calendar_metadata(
    calendar_name: str | None,
    calendar_uid: str | None,
    sync_provider: str | None = "calendar",
) -> str:
    if not calendar_name or not calendar_uid:
        return ""
    metadata = json.dumps(
        {
            "provider": sync_provider,
            "name": calendar_name,
            "uid": calendar_uid,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f" <!-- calendar: {metadata} -->"


def task_line(
    title: str,
    *,
    completed: bool,
    action_date: str | None,
    completed_date: str | None = None,
    calendar_name: str | None = None,
    calendar_uid: str | None = None,
    sync_provider: str | None = None,
) -> str:
    line = f"- [{'x' if completed else ' '}] {title}"
    if action_date:
        line += f" 📅 {action_date}"
    if completed_date:
        line += f" ✅ {completed_date}"
    return line + calendar_metadata(
        calendar_name,
        calendar_uid,
        sync_provider,
    )


def add_task(
    vault: Path,
    title: str,
    area: str | None,
    project: str | None,
    action_date: str | None,
    parent_line: int | None = None,
) -> dict[str, Any]:
    if "\n" in title or "\r" in title:
        raise CommandCenterError("Task title must fit on one line.")
    if "📅" in title or "✅" in title:
        raise CommandCenterError(
            "Task title cannot contain reserved date markers (📅 or ✅)."
        )
    title = " ".join(title.split())
    if not title:
        raise CommandCenterError("Task title cannot be empty.")
    if area and project:
        raise CommandCenterError("Use either --area or --project, not both.")
    if action_date:
        validate_iso_date(action_date)
    if parent_line is not None and (parent_line < 1 or not action_date):
        raise CommandCenterError(
            "A parent line requires a positive line number and dated task."
        )
    if area == "Work" and action_date:
        raise CommandCenterError(
            "Dated Work tasks must be added with work-task-add."
        )

    if project:
        section = project_by_name(vault, project).name
    elif area:
        section = area.title()
    else:
        section = "Inbox"

    sync_provider = None
    calendar_name = None
    calendar_uid = None
    if action_date:
        sync_provider = "reminders"
        calendar_name = "Reminders"
        calendar_uid = add_synced_todo(
            sync_provider,
            calendar_name,
            title,
            action_date,
        )

    tasks_path = vault / TASKS_RELATIVE_PATH
    with path_lock(tasks_path):
        tasks_path = ensure_tasks_file(vault)
        ensure_task_section(tasks_path, section)
        line = task_line(
            title,
            completed=False,
            action_date=action_date,
            calendar_name=calendar_name,
            calendar_uid=calendar_uid,
            sync_provider=sync_provider,
        )
        append_task(tasks_path, section, line)
    daily_path = None
    if action_date and section_uses_personal_daily(vault, section):
        daily_path = append_personal_daily_task(
            vault,
            title,
            action_date,
            parent_line,
        )
    audit_event(
        "added",
        "task",
        title,
        {"area": section, "date": action_date, "parent_line": parent_line},
    )
    reconcile_next_day(vault, action_date)
    return {
        "title": title,
        "section": section,
        "action_date": action_date,
        "status": "open",
        "calendar": calendar_name,
        "calendar_uid": calendar_uid,
        "sync_provider": sync_provider,
        "daily_path": daily_path,
        "parent_line": parent_line,
    }


def task_matches(tasks: list[Task], query: str) -> list[Task]:
    normalized = " ".join(query.split()).casefold()
    open_tasks = [task for task in tasks if not task.completed]
    exact = [task for task in open_tasks if task.title.casefold() == normalized]
    if exact:
        return exact
    return [task for task in open_tasks if normalized in task.title.casefold()]


def select_task(
    tasks_path: Path,
    query: str,
    action_date: str | None = None,
) -> Task:
    matches = task_matches(parse_tasks(tasks_path), query)
    if action_date:
        matches = [task for task in matches if task.action_date == action_date]
    if not matches:
        raise CommandCenterError(f"No open task matches: {query}")
    if len(matches) > 1:
        raise CommandCenterError(
            f"Multiple open tasks match: {query}",
            [asdict(task) for task in matches],
        )
    return matches[0]


def replace_task_line(tasks_path: Path, task: Task, new_line: str) -> None:
    lines = tasks_path.read_text(encoding="utf-8").splitlines()
    index = task.line_number - 1
    if index >= len(lines) or not TASK_PATTERN.match(lines[index]):
        raise CommandCenterError("Tasks file changed while the task was selected.")
    lines[index] = new_line
    atomic_write(tasks_path, "\n".join(lines).rstrip() + "\n")


def complete_task(
    vault: Path,
    query: str,
    action_date: str | None = None,
) -> dict[str, Any]:
    tasks_path = vault / TASKS_RELATIVE_PATH
    with path_lock(tasks_path):
        task = select_task(tasks_path, query, action_date)
        completed_date = date.today().isoformat()
        if task.calendar_name and task.calendar_uid:
            update_synced_todo(
                task.sync_provider or "calendar",
                task.calendar_name,
                task.calendar_uid,
                title=task.title,
                completed=True,
            )
        line = task_line(
            task.title,
            completed=True,
            action_date=task.action_date,
            completed_date=completed_date,
            calendar_name=task.calendar_name,
            calendar_uid=task.calendar_uid,
            sync_provider=task.sync_provider,
        )
        replace_task_line(tasks_path, task, line)
    daily_synced = False
    if task.action_date and section_uses_personal_daily(vault, task.section):
        daily_synced = complete_personal_daily_task(
            vault,
            task.title,
            task.action_date,
        )
    audit_event(
        "completed",
        "task",
        task.title,
        {"area": task.section, "date": task.action_date},
    )
    reconcile_next_day(vault, task.action_date)
    return {
        "title": task.title,
        "section": task.section,
        "status": "completed",
        "completed_date": completed_date,
        "daily_synced": daily_synced,
    }


def reopen_task(
    vault: Path,
    query: str,
    action_date: str,
) -> dict[str, Any]:
    validate_iso_date(action_date)
    normalized = " ".join(query.split()).casefold()
    tasks_path = vault / TASKS_RELATIVE_PATH
    with path_lock(tasks_path):
        matches = [
            task
            for task in parse_tasks(tasks_path)
            if task.completed
            and task.action_date == action_date
            and task.title.casefold() == normalized
        ]
        if len(matches) != 1:
            raise CommandCenterError(
                f"Expected one completed task matching: {query}",
                [asdict(task) for task in matches],
            )
        task = matches[0]
        if task.calendar_name and task.calendar_uid:
            update_synced_todo(
                task.sync_provider or "reminders",
                task.calendar_name,
                task.calendar_uid,
                title=task.title,
                action_date=action_date,
                completed=False,
            )
        line = task_line(
            task.title,
            completed=False,
            action_date=action_date,
            calendar_name=task.calendar_name,
            calendar_uid=task.calendar_uid,
            sync_provider=task.sync_provider,
        )
        replace_task_line(tasks_path, task, line)
    daily_synced = False
    if section_uses_personal_daily(vault, task.section):
        daily_synced = reopen_personal_daily_task(
            vault,
            task.title,
            action_date,
        )
    audit_event(
        "reopened",
        "task",
        task.title,
        {"area": task.section, "date": action_date},
    )
    reconcile_next_day(vault, action_date)
    return {
        "title": task.title,
        "section": task.section,
        "status": "open",
        "date": action_date,
        "daily_synced": daily_synced,
    }


def delete_task(
    vault: Path,
    query: str,
    action_date: str,
) -> dict[str, Any]:
    validate_iso_date(action_date)
    normalized = " ".join(query.split()).casefold()
    immediate_children = [
        item
        for item in list_daily_tasks(vault, action_date, True)["personal"]
        if item.get("parent_path")
        and item["parent_path"][-1].casefold() == normalized
    ]
    for child in immediate_children:
        delete_task(vault, child["title"], action_date)
    tasks_path = vault / TASKS_RELATIVE_PATH
    with path_lock(tasks_path):
        matches = [
            task
            for task in parse_tasks(tasks_path)
            if task.action_date == action_date
            and task.title.casefold() == normalized
            and not task.title.endswith("→ διαγράφηκε")
        ]
        if len(matches) != 1:
            raise CommandCenterError(
                f"Expected one task matching: {query}",
                [asdict(task) for task in matches],
            )
        task = matches[0]
        if task.calendar_uid:
            if (task.sync_provider or "reminders") == "reminders":
                delete_reminder_item(
                    task.calendar_name or "Reminders",
                    task.calendar_uid,
                )
            else:
                delete_calendar_event(
                    task.calendar_name or "Work",
                    task.calendar_uid,
                )
        line = task_line(
            f"{task.title} → διαγράφηκε",
            completed=True,
            action_date=action_date,
            completed_date=date.today().isoformat(),
        )
        replace_task_line(tasks_path, task, line)
    daily_synced = False
    if section_uses_personal_daily(vault, task.section):
        daily_synced = delete_personal_daily_task(
            vault,
            task.title,
            action_date,
        )
    audit_event(
        "deleted",
        "task",
        task.title,
        {"area": task.section, "date": action_date},
    )
    reconcile_next_day(vault, action_date)
    return {
        "title": task.title,
        "section": task.section,
        "status": "deleted",
        "date": action_date,
        "daily_synced": daily_synced,
    }


def reschedule_task(vault: Path, query: str, action_date: str) -> dict[str, Any]:
    validate_iso_date(action_date)
    tasks_path = vault / TASKS_RELATIVE_PATH
    with path_lock(tasks_path):
        task = select_task(tasks_path, query)
        sync_provider = task.sync_provider or "reminders"
        calendar_name = task.calendar_name or "Reminders"
        calendar_uid = task.calendar_uid
        if calendar_uid:
            update_synced_todo(
                sync_provider,
                calendar_name,
                calendar_uid,
                title=task.title,
                action_date=action_date,
                completed=False,
            )
        else:
            calendar_uid = add_synced_todo(
                sync_provider,
                calendar_name,
                task.title,
                action_date,
            )
        line = task_line(
            task.title,
            completed=False,
            action_date=action_date,
            calendar_name=calendar_name,
            calendar_uid=calendar_uid,
            sync_provider=sync_provider,
        )
        replace_task_line(tasks_path, task, line)
    daily_path = None
    if section_uses_personal_daily(vault, task.section):
        if task.action_date and task.action_date != action_date:
            daily_path = move_personal_daily_task(
                vault,
                task.title,
                task.action_date,
                action_date,
            )
        else:
            daily_path = append_personal_daily_task(
                vault,
                task.title,
                action_date,
            )
    audit_event(
        "rescheduled",
        "task",
        task.title,
        {
            "area": task.section,
            "from_date": task.action_date,
            "to_date": action_date,
        },
    )
    reconcile_next_day(vault, task.action_date)
    reconcile_next_day(vault, action_date)
    return {
        "title": task.title,
        "section": task.section,
        "status": "open",
        "action_date": action_date,
        "calendar": calendar_name,
        "calendar_uid": calendar_uid,
        "sync_provider": sync_provider,
        "daily_path": daily_path,
    }


def update_task(
    vault: Path,
    query: str,
    current_date: str,
    new_title: str,
    new_date: str,
) -> dict[str, Any]:
    validate_iso_date(current_date)
    validate_iso_date(new_date)
    new_title = " ".join(new_title.split())
    if not new_title or "\n" in new_title or "\r" in new_title:
        raise CommandCenterError("Task title must fit on one non-empty line.")
    tasks_path = vault / TASKS_RELATIVE_PATH
    with path_lock(tasks_path):
        task = select_task(tasks_path, query, current_date)
        sync_provider = task.sync_provider or "reminders"
        calendar_name = task.calendar_name or "Reminders"
        calendar_uid = task.calendar_uid
        if calendar_uid:
            update_synced_todo(
                sync_provider,
                calendar_name,
                calendar_uid,
                title=new_title,
                action_date=new_date,
                completed=False,
            )
        else:
            calendar_uid = add_synced_todo(
                sync_provider,
                calendar_name,
                new_title,
                new_date,
            )
        line = task_line(
            new_title,
            completed=False,
            action_date=new_date,
            calendar_name=calendar_name,
            calendar_uid=calendar_uid,
            sync_provider=sync_provider,
        )
        replace_task_line(tasks_path, task, line)
    daily_path = None
    if section_uses_personal_daily(vault, task.section):
        daily_path = update_personal_daily_task(
            vault,
            task.title,
            current_date,
            new_title,
            new_date,
        )
    audit_event(
        "updated",
        "task",
        new_title,
        {
            "old_title": task.title,
            "area": task.section,
            "from_date": current_date,
            "to_date": new_date,
        },
    )
    reconcile_next_day(vault, current_date)
    if new_date != current_date:
        reconcile_next_day(vault, new_date)
    return {
        "title": new_title,
        "old_title": task.title,
        "section": task.section,
        "from_date": current_date,
        "to_date": new_date,
        "calendar": calendar_name,
        "calendar_uid": calendar_uid,
        "daily_path": daily_path,
    }


def run_process(command: list[str], *, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise IntegrationError(f"Cannot run {command[0]}: {exc}") from exc
    if result.returncode != 0 and not allow_failure:
        message = result.stderr.strip() or result.stdout.strip()
        raise IntegrationError(f"{' '.join(command)} failed: {message}")
    return result


def run_json(command: list[str], *, allow_failure: bool = False) -> Any:
    result = run_process(command, allow_failure=allow_failure)
    if not result.stdout.strip():
        if result.returncode != 0:
            message = result.stderr.strip()
            if "no checks reported" not in message.lower():
                raise IntegrationError(
                    f"{' '.join(command)} failed: {message or 'no output'}"
                )
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise IntegrationError(
            f"{' '.join(command)} returned invalid JSON."
        ) from exc


def parse_json_stream(output: str) -> list[Any]:
    decoder = json.JSONDecoder()
    position = 0
    values: list[Any] = []
    while position < len(output):
        while position < len(output) and output[position].isspace():
            position += 1
        if position >= len(output):
            break
        try:
            value, position = decoder.raw_decode(output, position)
        except json.JSONDecodeError as exc:
            raise IntegrationError("Integration returned invalid JSON stream.") from exc
        values.append(value)
    return values


def redact_external_text(value: str) -> str:
    redacted = ANSI_PATTERN.sub("", value)
    redacted = EMAIL_PATTERN.sub("<EMAIL>", redacted)
    redacted = re.sub(
        r"(?i)(authorization[:=]\s*(?:bearer\s+)?)(\S+)",
        r"\1<REDACTED>",
        redacted,
    )
    redacted = re.sub(
        r"(?i)((?:api[_-]?key|token|secret|password)[:=]\s*)(\S+)",
        r"\1<REDACTED>",
        redacted,
    )
    return redacted


def mask_email(value: str) -> str:
    match = EMAIL_PATTERN.fullmatch(value.strip())
    if not match:
        return "<REDACTED>"
    local, domain = value.strip().rsplit("@", 1)
    visible = local[:1]
    return f"{visible}***@{domain}"


def github_attention(repository: str | None = None) -> dict[str, Any]:
    authored = run_json(
        [
            "gh",
            "search",
            "prs",
            "--author",
            "@me",
            "--state",
            "open",
            "--limit",
            "100",
            "--json",
            "number,title,repository,url,isDraft,updatedAt",
        ]
    )
    reviews = run_json(
        [
            "gh",
            "search",
            "prs",
            "--review-requested",
            "@me",
            "--state",
            "open",
            "--limit",
            "100",
            "--json",
            "number,title,repository,url,isDraft,updatedAt",
        ]
    )
    if repository:
        authored = [
            pull_request
            for pull_request in authored
            if pull_request["repository"]["nameWithOwner"].casefold()
            == repository.casefold()
        ]
        reviews = [
            pull_request
            for pull_request in reviews
            if pull_request["repository"]["nameWithOwner"].casefold()
            == repository.casefold()
        ]

    failures: list[dict[str, Any]] = []
    unknown_checks: list[dict[str, Any]] = []
    for pull_request in authored:
        try:
            checks = run_json(
                [
                    "gh",
                    "pr",
                    "checks",
                    pull_request["url"],
                    "--json",
                    "bucket,name,state,link",
                ],
                allow_failure=True,
            )
        except IntegrationError as exc:
            unknown_checks.append(
                {
                    "url": pull_request["url"],
                    "repository": pull_request["repository"]["nameWithOwner"],
                    "number": pull_request["number"],
                    "title": pull_request["title"],
                    "error": str(exc),
                }
            )
            continue
        failed_checks = [
            check
            for check in checks
            if check.get("bucket") in {"fail", "cancel"}
        ]
        if failed_checks:
            failures.append(
                {
                    "url": pull_request["url"],
                    "repository": pull_request["repository"]["nameWithOwner"],
                    "number": pull_request["number"],
                    "title": pull_request["title"],
                    "checks": failed_checks,
                }
            )
    return {
        "authored_open": authored,
        "review_requested": reviews,
        "failing_ci": failures,
        "unknown_ci": unknown_checks,
    }


def project_status(vault: Path, name: str) -> dict[str, Any]:
    project = project_by_name(vault, name)
    note = vault / project.note_path
    return {
        "project": asdict(project),
        "summary": project_summary(note),
        "recent_records": [
            asdict(record) for record in project_records(note)[-10:]
        ],
        "tasks": list_tasks(vault, "all", project.name),
        "github": github_attention(project.github) if project.github else None,
        "health": project_health(vault, project.name),
    }


def render_service_names(project_path: Path) -> list[str]:
    config = next(
        (
            candidate
            for candidate in (
                project_path / "render.yaml",
                project_path / "render.yml",
            )
            if candidate.is_file()
        ),
        None,
    )
    if config is None:
        return []
    names: list[str] = []
    for line in config.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s+name:\s*[\"']?([^\"'#]+)", line)
        if match:
            names.append(match.group(1).strip())
    return list(dict.fromkeys(names))


def github_from_remote(project_path: Path) -> str | None:
    result = run_process(
        ["git", "-C", str(project_path), "remote", "get-url", "origin"],
        allow_failure=True,
    )
    if result.returncode != 0:
        return None
    remote = result.stdout.strip()
    patterns = (
        r"^https://github\.com/(?P<repo>[^/]+/[^/]+?)(?:\.git)?$",
        r"^git@github\.com:(?P<repo>[^/]+/[^/]+?)(?:\.git)?$",
        r"^ssh://git@github\.com/(?P<repo>[^/]+/[^/]+?)(?:\.git)?$",
    )
    for pattern in patterns:
        match = re.match(pattern, remote)
        if match:
            return match.group("repo")
    return None


def portable_path(path: Path) -> str:
    try:
        return f"~/{path.relative_to(Path.home())}"
    except ValueError:
        return str(path)


def project_note_content(project: Project) -> str:
    def scalar(value: str) -> str:
        return json.dumps(value, ensure_ascii=False)

    lines = [
        "---",
        f"name: {scalar(project.name)}",
        f"status: {project.status}",
        f"area: {project.area}",
        f"lifecycle: {project.lifecycle}",
    ]
    if project.local_path:
        lines.append(f"local_path: {scalar(project.local_path)}")
    if project.github:
        lines.append(f"github: {scalar(project.github)}")
    lines.append("render_services:")
    lines.extend(f"  - {scalar(name)}" for name in project.render_services)
    lines.append("render_service_ids:")
    lines.extend(f"  - {scalar(identifier)}" for identifier in project.render_service_ids)
    lines.append("resend_domains:")
    lines.extend(f"  - {scalar(domain)}" for domain in project.resend_domains)
    lines.append("source_paths:")
    lines.extend(f"  - {scalar(path)}" for path in project.source_paths)
    lines.append("health_checks:")
    lines.extend(f"  - {scalar(check)}" for check in project.health_checks)
    lines.extend(
        [
            "---",
            "",
            f"# {project.name}",
            "",
            "## Σύνοψη",
            "",
            "Δεν έχει οριστεί ακόμη.",
            "",
            "## Καταγραφές",
            "",
        ]
    )
    return "\n".join(lines)


def validate_project_metadata(
    render_service_ids: list[str],
    resend_domains: list[str],
    source_paths: list[str],
    health_checks: list[str],
) -> None:
    for identifier in render_service_ids:
        if not re.fullmatch(r"srv-[a-z0-9]+", identifier):
            raise CommandCenterError(f"Invalid Render service ID: {identifier}")
    domain_pattern = re.compile(
        r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}"
    )
    for domain in resend_domains:
        if not domain_pattern.fullmatch(domain):
            raise CommandCenterError(f"Invalid Resend domain: {domain}")
    for source_path in source_paths:
        parsed = Path(source_path)
        if parsed.is_absolute() or ".." in parsed.parts or "\\" in source_path:
            raise CommandCenterError(
                f"Project source path must be vault-relative: {source_path}"
            )
    for health_check in health_checks:
        parse_health_check(health_check)


def project_note(vault: Path, name: str) -> Path:
    project = project_by_name(vault, name)
    return vault / project.note_path


def markdown_section_bounds(lines: list[str], heading: str) -> tuple[int, int] | None:
    start: int | None = None
    for index, line in enumerate(lines):
        if line == f"## {heading}":
            start = index
            continue
        if start is not None and line.startswith("## "):
            return start, index
    if start is None:
        return None
    return start, len(lines)


def project_summary(note: Path) -> str:
    lines = note.read_text(encoding="utf-8").splitlines()
    bounds = markdown_section_bounds(lines, "Σύνοψη")
    if bounds is None:
        return ""
    start, end = bounds
    return "\n".join(lines[start + 1 : end]).strip()


def project_records(note: Path) -> list[ProjectRecord]:
    lines = note.read_text(encoding="utf-8").splitlines()
    bounds = markdown_section_bounds(lines, "Καταγραφές")
    if bounds is None:
        return []
    start, end = bounds
    records: list[ProjectRecord] = []
    index = start + 1
    while index < end:
        heading = RECORD_HEADING_PATTERN.match(lines[index])
        if not heading:
            index += 1
            continue
        block_end = index + 1
        while block_end < end and not lines[block_end].startswith("### "):
            block_end += 1
        block = lines[index + 1 : block_end]
        record_id = ""
        record_timestamp = heading.group("timestamp")
        source = ""
        supersedes: str | None = None
        text_lines: list[str] = []
        for line in block:
            id_match = RECORD_ID_PATTERN.match(line)
            timestamp_match = RECORD_TIMESTAMP_PATTERN.match(line)
            if id_match:
                record_id = id_match.group("id")
            elif timestamp_match:
                record_timestamp = timestamp_match.group("timestamp")
            elif line.startswith("- Πηγή: "):
                source = line.removeprefix("- Πηγή: ").strip()
            elif line.startswith("- Αντικαθιστά: "):
                supersedes = line.removeprefix("- Αντικαθιστά: ").strip()
            elif line.strip():
                text_lines.append(line.strip())
        label = heading.group("label")
        records.append(
            ProjectRecord(
                id=record_id,
                timestamp=record_timestamp,
                kind=RECORD_LABEL_KINDS.get(label, label),
                text=" ".join(text_lines),
                source=source,
                supersedes=supersedes,
                active=True,
            )
        )
        index = block_end

    superseded_ids = {
        record.supersedes for record in records if record.supersedes
    }
    for record in records:
        record.active = record.id not in superseded_ids
    return records


def validate_project_memory(text: str, source: str) -> tuple[str, str]:
    normalized_text = " ".join(text.split())
    normalized_source = " ".join(source.split())
    if not normalized_text:
        raise CommandCenterError("Project record text cannot be empty.")
    if not normalized_source:
        raise CommandCenterError("Project record source cannot be empty.")
    values = (normalized_text, normalized_source)
    if any(
        SENSITIVE_VALUE_PATTERN.search(value)
        or SENSITIVE_SHAPE_PATTERN.search(value)
        for value in values
    ):
        raise CommandCenterError(
            "Project memory cannot contain credential-like values."
        )
    return normalized_text, normalized_source


def project_record_block(
    kind: str,
    text: str,
    source: str,
    supersedes: str | None,
) -> tuple[str, ProjectRecord]:
    normalized_text, normalized_source = validate_project_memory(text, source)
    now = datetime.now().astimezone()
    timestamp = now.isoformat(timespec="seconds")
    record_id = f"{now.strftime('%Y%m%dT%H%M%S%z')}-{uuid.uuid4().hex[:6]}"
    display_time = now.strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"### {display_time} · {RECORD_KIND_LABELS[kind]}",
        f"<!-- id: {record_id} -->",
        f"<!-- timestamp: {timestamp} -->",
        normalized_text,
        "",
        f"- Πηγή: {normalized_source}",
    ]
    if supersedes:
        lines.append(f"- Αντικαθιστά: {supersedes}")
    lines.append("")
    return (
        "\n".join(lines),
        ProjectRecord(
            id=record_id,
            timestamp=timestamp,
            kind=kind,
            text=normalized_text,
            source=normalized_source,
            supersedes=supersedes,
            active=True,
        ),
    )


def append_record_to_content(content: str, block: str) -> str:
    lines = content.splitlines()
    bounds = markdown_section_bounds(lines, "Καταγραφές")
    if bounds is None:
        return content.rstrip() + f"\n\n## Καταγραφές\n\n{block}"
    _, end = bounds
    before = "\n".join(lines[:end]).rstrip()
    after = "\n".join(lines[end:]).lstrip()
    updated = f"{before}\n\n{block.rstrip()}\n"
    if after:
        updated += f"\n{after}\n"
    return updated


def replace_summary_in_content(content: str, summary: str) -> str:
    lines = content.splitlines()
    bounds = markdown_section_bounds(lines, "Σύνοψη")
    if bounds is None:
        heading_index = next(
            (index for index, line in enumerate(lines) if line.startswith("# ")),
            len(lines) - 1,
        )
        insert_at = heading_index + 1
        lines[insert_at:insert_at] = ["", "## Σύνοψη", "", summary]
        return "\n".join(lines).rstrip() + "\n"
    start, end = bounds
    lines[start + 1 : end] = ["", summary, ""]
    return "\n".join(lines).rstrip() + "\n"


def record_project(
    vault: Path,
    name: str,
    kind: str,
    text: str,
    source: str,
    supersedes: str | None,
) -> ProjectRecord:
    note = project_note(vault, name)
    with path_lock(note):
        existing = project_records(note)
        if supersedes and supersedes not in {record.id for record in existing}:
            raise CommandCenterError(f"Unknown superseded record: {supersedes}")
        block, record = project_record_block(kind, text, source, supersedes)
        atomic_write(
            note,
            append_record_to_content(note.read_text(encoding="utf-8"), block),
        )
    audit_event(
        "recorded",
        "project",
        name,
        {"kind": kind, "record_id": record.id},
    )
    return record


def archive_project_record(
    vault: Path,
    name: str,
    record_id: str,
    source: str,
) -> dict[str, Any]:
    note = project_note(vault, name)
    with path_lock(note):
        records = project_records(note)
        matches = [
            record
            for record in records
            if record.id == record_id and record.kind == "note" and record.active
        ]
        if len(matches) != 1:
            raise CommandCenterError("Active project note was not found.")
        block, archive = project_record_block(
            "archive",
            "Η σημείωση έργου αρχειοθετήθηκε.",
            source,
            record_id,
        )
        atomic_write(
            note,
            append_record_to_content(note.read_text(encoding="utf-8"), block),
        )
    audit_event(
        "deleted",
        "project-note",
        name,
        {"record_id": record_id, "archive_id": archive.id},
    )
    return {
        "project": name,
        "record_id": record_id,
        "status": "archived",
        "archive": asdict(archive),
    }


def set_project_summary(
    vault: Path,
    name: str,
    summary: str,
    source: str,
) -> dict[str, Any]:
    note = project_note(vault, name)
    with path_lock(note):
        block, record = project_record_block(
            "summary",
            summary,
            source,
            None,
        )
        content = append_record_to_content(note.read_text(encoding="utf-8"), block)
        content = replace_summary_in_content(content, record.text)
        atomic_write(note, content)
    return {"summary": record.text, "record": asdict(record)}


def replace_frontmatter_list(
    content: str,
    key: str,
    values: list[str],
) -> str:
    lines = content.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if line == f"{key}:"),
        None,
    )
    if start is None:
        raise CommandCenterError(f"Project frontmatter has no '{key}' field.")
    end = start + 1
    while end < len(lines) and lines[end].startswith("  - "):
        end += 1
    replacement = [f"{key}:"]
    replacement.extend(
        f"  - {json.dumps(value, ensure_ascii=False)}"
        for value in values
    )
    lines[start:end] = replacement
    return "\n".join(lines).rstrip() + "\n"


def set_project_health_checks(
    vault: Path,
    name: str,
    health_checks: list[str],
    source: str,
) -> dict[str, Any]:
    project = project_by_name(vault, name)
    validate_project_metadata([], [], [], health_checks)
    note = vault / project.note_path
    with path_lock(note):
        block, record = project_record_block(
            "decision",
            "Τα automated health checks χρησιμοποιούν liveness endpoints "
            "που δεν κάνουν database ping.",
            source,
            None,
        )
        content = replace_frontmatter_list(
            note.read_text(encoding="utf-8"),
            "health_checks",
            health_checks,
        )
        content = append_record_to_content(content, block)
        atomic_write(note, content)
    return {
        "project": project.name,
        "health_checks": health_checks,
        "record": asdict(record),
    }


def add_project(
    vault: Path,
    name: str | None,
    area: str,
    lifecycle: str,
    local_path: str | None,
    github: str | None,
    render_service_ids: list[str],
    resend_domains: list[str],
    source_paths: list[str],
    health_checks: list[str],
) -> Project:
    resolved_path: Path | None = None
    if local_path:
        resolved_path = Path(local_path).expanduser().resolve()
        if not resolved_path.is_dir():
            raise CommandCenterError(f"Project path does not exist: {resolved_path}")
    if not name:
        if resolved_path:
            name = resolved_path.name
        elif github:
            name = github.rsplit("/", 1)[-1]
        else:
            raise CommandCenterError("Provide --name, --path, or --github.")
    name = " ".join(name.split())
    if not re.match(r"^[^/\\:]+$", name):
        raise CommandCenterError("Project name cannot contain '/', '\\', or ':'.")
    if name.casefold() in {"inbox", "personal", "work"}:
        raise CommandCenterError(
            f"Project name is reserved and cannot be used: {name}"
        )
    validate_project_metadata(
        render_service_ids,
        resend_domains,
        source_paths,
        health_checks,
    )

    projects_dir = vault / PROJECTS_RELATIVE_PATH
    projects_dir.mkdir(parents=True, exist_ok=True)
    note = projects_dir / f"{name}.md"
    with path_lock(note):
        if note.exists():
            raise CommandCenterError(f"Project already exists: {name}")

        discovered_github = github
        services: list[str] = []
        if resolved_path:
            discovered_github = discovered_github or github_from_remote(resolved_path)
            services = render_service_names(resolved_path)

        project = Project(
            name=name,
            area=area,
            status="active",
            lifecycle=lifecycle,
            local_path=portable_path(resolved_path) if resolved_path else None,
            github=discovered_github,
            render_services=services,
            render_service_ids=render_service_ids,
            resend_domains=resend_domains,
            source_paths=source_paths,
            health_checks=health_checks,
            note_path=str(note.relative_to(vault)),
        )
        atomic_write(note, project_note_content(project))
        tasks_path = vault / TASKS_RELATIVE_PATH
        with path_lock(tasks_path):
            tasks_path = ensure_tasks_file(vault)
            ensure_task_section(tasks_path, project.name)
    return project


def run_osascript(script: str, arguments: list[str] | None = None) -> str:
    command = ["osascript", "-"]
    if arguments:
        command.extend(arguments)
    try:
        result = subprocess.run(
            command,
            input=script,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise IntegrationError(f"Cannot run osascript: {exc}") from exc
    if result.returncode != 0:
        raise IntegrationError(result.stderr.strip() or "AppleScript failed.")
    return result.stdout.strip()


APPLE_SCRIPT_HELPERS = r'''
on pad2(n)
    if n < 10 then return "0" & n
    return n as text
end pad2

on isoDate(d)
    return (year of d as integer) & "-" & my pad2(month of d as integer) & "-" & my pad2(day of d) & "T" & my pad2(hours of d) & ":" & my pad2(minutes of d)
end isoDate

on replaceText(findText, replacementText, sourceText)
    set previousDelimiters to AppleScript's text item delimiters
    set AppleScript's text item delimiters to findText
    set sourceItems to text items of sourceText
    set AppleScript's text item delimiters to replacementText
    set cleanText to sourceItems as text
    set AppleScript's text item delimiters to previousDelimiters
    return cleanText
end replaceText

on cleanText(sourceText)
    set sourceText to my replaceText(tab, " ", sourceText)
    set sourceText to my replaceText(return, " ", sourceText)
    return my replaceText(linefeed, " ", sourceText)
end cleanText
'''


def parse_tabular_output(output: str, fields: list[str]) -> list[dict[str, str]]:
    if not output.strip() or output.strip() == "missing value":
        return []
    items: list[dict[str, str]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        values = line.split("\t", len(fields) - 1)
        if len(values) < len(fields):
            values.extend([""] * (len(fields) - len(values)))
        if len(values) != len(fields):
            raise IntegrationError("macOS integration returned malformed output.")
        items.append(dict(zip(fields, values, strict=True)))
    return items


def calendar_names() -> list[str]:
    script = r'''
tell application "Calendar"
    set calendarNames to name of every calendar
end tell
set AppleScript's text item delimiters to linefeed
return calendarNames as text
'''
    output = run_osascript(script)
    return [name for name in output.splitlines() if name.strip()]


def calendar_events_today() -> list[dict[str, str]]:
    script = APPLE_SCRIPT_HELPERS + r'''
set startDate to current date
set time of startDate to 0
set endDate to startDate + (1 * days)
set output to {}
tell application "Calendar"
    repeat with cal in calendars
        set calName to name of cal
        set matchingEvents to every event of cal whose start date < endDate and end date > startDate
        repeat with evt in matchingEvents
            try
                set rawURL to url of evt
                if rawURL is missing value then
                    set eventURL to ""
                else
                    set eventURL to my cleanText(rawURL as text)
                end if
            on error
                set eventURL to ""
            end try
            try
                set rawDescription to description of evt
                if rawDescription is missing value then
                    set eventDescription to ""
                else
                    set eventDescription to my cleanText(rawDescription as text)
                end if
            on error
                set eventDescription to ""
            end try
            try
                set eventUID to uid of evt as text
            on error
                set eventUID to ""
            end try
            set eventLine to my cleanText(calName) & tab & my cleanText(summary of evt) & tab & my isoDate(start date of evt) & tab & my isoDate(end date of evt) & tab & (allday event of evt as text) & tab & eventURL & tab & eventDescription & tab & eventUID
            set end of output to eventLine
        end repeat
    end repeat
end tell
set AppleScript's text item delimiters to linefeed
return output as text
'''
    events = parse_tabular_output(
        run_osascript(script),
        [
            "calendar",
            "title",
            "start",
            "end",
            "all_day",
            "url",
            "description",
            "uid",
        ],
    )
    events.sort(key=lambda event: (event["start"], event["calendar"], event["title"]))
    return events


def reminders_today() -> list[dict[str, Any]]:
    script = APPLE_SCRIPT_HELPERS + r'''
set startDate to current date
set time of startDate to 0
set endDate to startDate + (1 * days)
set output to {}
tell application "Reminders"
    repeat with targetList in lists
        set listName to name of targetList
        repeat with reminderItem in reminders of targetList
            try
                set dueDate to due date of reminderItem
                if dueDate is not missing value and dueDate >= startDate and dueDate < endDate then
                    set reminderLine to my cleanText(listName) & tab & my cleanText(name of reminderItem) & tab & my isoDate(dueDate) & tab & (completed of reminderItem as text) & tab & my cleanText(id of reminderItem)
                    set end of output to reminderLine
                end if
            end try
        end repeat
    end repeat
end tell
set AppleScript's text item delimiters to linefeed
return output as text
'''
    reminders = parse_tabular_output(
        run_osascript(script),
        ["list", "title", "due", "completed", "id"],
    )
    return [
        {
            "calendar": reminder["list"],
            "title": reminder["title"],
            "start": reminder["due"],
            "end": reminder["due"],
            "all_day": "true",
            "kind": "reminder",
            "url": "",
            "description": "",
            "completed": reminder["completed"] == "true",
            "uid": reminder["id"],
        }
        for reminder in reminders
    ]


def calendar_today() -> list[dict[str, Any]]:
    events = calendar_events_today()
    now = datetime.now()
    for event in events:
        calendar = event["calendar"].casefold()
        event["kind"] = (
            "birthday"
            if "birthday" in calendar
            else "holiday"
            if "holiday" in calendar
            else "note"
            if "note" in calendar
            else "event"
        )
        event["completed"] = (
            event["title"].startswith("✓ ")
            or (
                event["all_day"] == "false"
                and datetime.fromisoformat(event["end"]) <= now
            )
        )
        ref_match = re.search(r"(?:^|\s)Ref:\s*([A-Za-z0-9]+)", event["description"])
        event["command_center_ref"] = (
            ref_match.group(1) if ref_match else None
        )
    events.extend(reminders_today())
    events.sort(key=lambda event: (event["start"], event["calendar"], event["title"]))
    return events


def delete_calendar_event(calendar: str, event_uid: str) -> bool:
    script = r'''
on run argv
    set calendarName to item 1 of argv
    set eventUID to item 2 of argv
    tell application "Calendar"
        set targetCalendar to calendar calendarName
        set matches to every event of targetCalendar whose uid is eventUID
        if (count of matches) is 0 then error "Calendar event not found"
        delete item 1 of matches
    end tell
end run
'''
    try:
        run_osascript(script, [calendar, event_uid])
        return True
    except IntegrationError as exc:
        if "Calendar event not found" in str(exc):
            return False
        raise


def delete_calendar_event_by_ref(calendar: str, calendar_ref: str) -> bool:
    script = r'''
on run argv
    set calendarName to item 1 of argv
    set calendarRef to item 2 of argv
    tell application "Calendar"
        set targetCalendar to calendar calendarName
        set matches to every event of targetCalendar whose description contains ("Ref: " & calendarRef)
        if (count of matches) is 0 then error "Calendar todo not found"
        delete item 1 of matches
    end tell
end run
'''
    try:
        run_osascript(script, [calendar, calendar_ref])
        return True
    except IntegrationError as exc:
        if "Calendar todo not found" in str(exc):
            return False
        raise


def delete_reminder_item(list_name: str, reminder_id: str) -> bool:
    script = r'''
on run argv
    set listName to item 1 of argv
    set reminderId to item 2 of argv
    tell application "Reminders"
        set targetList to list listName
        set matches to every reminder of targetList whose id is reminderId
        if (count of matches) is 0 then error "Reminder not found"
        delete item 1 of matches
    end tell
end run
'''
    try:
        run_osascript(script, [list_name, reminder_id])
        return True
    except IntegrationError as exc:
        if "Reminder not found" in str(exc):
            return False
        raise


def delete_agenda_item(
    vault: Path,
    kind: str,
    calendar: str,
    item_uid: str,
    title: str,
    command_center_ref: str | None,
) -> dict[str, Any]:
    if kind not in {"event", "reminder"}:
        raise CommandCenterError("Agenda kind must be event or reminder.")
    if not calendar or not item_uid or not title:
        raise CommandCenterError("Agenda delete requires calendar, UID, and title.")
    linked_task = None
    if kind == "reminder":
        linked_task = next(
            (
                task
                for task in parse_tasks(vault / TASKS_RELATIVE_PATH)
                if task.calendar_uid == item_uid
            ),
            None,
        )
        delete_reminder_item(calendar, item_uid)
        if linked_task and not linked_task.completed:
            tasks_path = vault / TASKS_RELATIVE_PATH
            with path_lock(tasks_path):
                line = task_line(
                    linked_task.title,
                    completed=True,
                    action_date=linked_task.action_date,
                    completed_date=date.today().isoformat(),
                )
                replace_task_line(tasks_path, linked_task, line)
            if linked_task.action_date:
                delete_personal_daily_task(
                    vault,
                    linked_task.title,
                    linked_task.action_date,
                )
    else:
        if command_center_ref:
            linked_task = next(
                (
                    task
                    for task in parse_work_tasks(vault)
                    if task.calendar_uid == command_center_ref
                ),
                None,
            )
        delete_calendar_event(calendar, item_uid)
        if linked_task and not linked_task.completed:
            note = vault / linked_task.path
            with path_lock(note):
                lines = note.read_text(encoding="utf-8").splitlines()
                index = linked_task.line_number - 1
                match = WORK_TASK_PATTERN.match(lines[index])
                if not match:
                    raise CommandCenterError(
                        "Work note changed while deleting Agenda item."
                    )
                lines[index] = (
                    f"{match.group('prefix')}[x] "
                    f"{linked_task.title} → διαγράφηκε"
                )
                atomic_write(note, "\n".join(lines).rstrip() + "\n")
    audit_event(
        "deleted",
        "agenda-item",
        title,
        {
            "kind": kind,
            "calendar": calendar,
            "linked_task": bool(linked_task),
        },
    )
    return {
        "title": title,
        "kind": kind,
        "calendar": calendar,
        "status": "deleted",
        "linked_task_closed": bool(linked_task),
    }


def calendar_upcoming(minutes: int) -> list[dict[str, str]]:
    if minutes < 1 or minutes > 1440:
        raise CommandCenterError(
            "Upcoming calendar range must be between 1 and 1440 minutes."
        )
    script = APPLE_SCRIPT_HELPERS + r'''
on run argv
    set rangeMinutes to item 1 of argv as integer
    set startDate to current date
    set endDate to startDate + (rangeMinutes * minutes)
    set output to {}
    tell application "Calendar"
        repeat with cal in calendars
            set calName to name of cal
            set matchingEvents to every event of cal whose start date > startDate and start date <= endDate and allday event is false
            repeat with evt in matchingEvents
                try
                    set rawURL to url of evt
                    if rawURL is missing value then
                        set eventURL to ""
                    else
                        set eventURL to my cleanText(rawURL as text)
                    end if
                on error
                    set eventURL to ""
                end try
                try
                    set rawDescription to description of evt
                    if rawDescription is missing value then
                        set eventDescription to ""
                    else
                        set eventDescription to my cleanText(rawDescription as text)
                    end if
                on error
                    set eventDescription to ""
                end try
                set eventLine to my cleanText(calName) & tab & my cleanText(summary of evt) & tab & my isoDate(start date of evt) & tab & my isoDate(end date of evt) & tab & "false" & tab & eventURL & tab & eventDescription
                set end of output to eventLine
            end repeat
        end repeat
    end tell
    set AppleScript's text item delimiters to linefeed
    return output as text
end run
'''
    events = parse_tabular_output(
        run_osascript(script, [str(minutes)]),
        ["calendar", "title", "start", "end", "all_day", "url", "description"],
    )
    for event in events:
        event["kind"] = "event"
    events.sort(key=lambda event: (event["start"], event["calendar"], event["title"]))
    return events


def calendar_range(days: int) -> list[dict[str, str]]:
    if days < 1 or days > 365:
        raise CommandCenterError("Calendar range must be between 1 and 365 days.")
    script = APPLE_SCRIPT_HELPERS + r'''
on run argv
    set rangeDays to item 1 of argv as integer
    set startDate to current date
    set endDate to startDate + (rangeDays * days)
    set output to {}
    tell application "Calendar"
        repeat with cal in calendars
            set calName to name of cal
            set matchingEvents to every event of cal whose start date < endDate and end date > startDate
            repeat with evt in matchingEvents
                set eventLine to my cleanText(calName) & tab & my cleanText(summary of evt) & tab & my isoDate(start date of evt) & tab & my isoDate(end date of evt) & tab & (allday event of evt as text)
                set end of output to eventLine
            end repeat
        end repeat
    end tell
    set AppleScript's text item delimiters to linefeed
    return output as text
end run
'''
    events = parse_tabular_output(
        run_osascript(script, [str(days)]),
        ["calendar", "title", "start", "end", "all_day"],
    )
    events.sort(key=lambda event: (event["start"], event["calendar"], event["title"]))
    return events


def add_synced_todo(
    provider: str,
    target: str,
    title: str,
    action_date: str,
) -> str:
    if provider == "reminders":
        return add_reminder_todo(target, title, action_date)
    if provider == "calendar":
        return add_calendar_todo(target, title, action_date)
    raise CommandCenterError(f"Unknown todo sync provider: {provider}")


def update_synced_todo(
    provider: str,
    target: str,
    identifier: str,
    *,
    title: str,
    action_date: str | None = None,
    completed: bool,
) -> None:
    if provider == "reminders":
        update_reminder_todo(
            target,
            identifier,
            title=title,
            action_date=action_date,
            completed=completed,
        )
        return
    if provider == "calendar":
        update_calendar_todo(
            target,
            identifier,
            title=title,
            action_date=action_date,
            completed=completed,
        )
        return
    raise CommandCenterError(f"Unknown todo sync provider: {provider}")


def reminder_list_names() -> list[str]:
    output = run_osascript(
        'tell application "Reminders" to get name of every list'
    )
    return [name.strip() for name in output.split(",") if name.strip()]


def add_reminder_item(
    list_name: str,
    title: str,
    action_date: str | None,
) -> str:
    title = " ".join(title.split())
    if not title or "\n" in title or "\r" in title:
        raise CommandCenterError("Reminder title must fit on one non-empty line.")
    if action_date:
        validate_iso_date(action_date)
    parsed_date = date.fromisoformat(action_date) if action_date else None
    if list_name not in reminder_list_names():
        raise CommandCenterError(f"Unknown macOS Reminders list: {list_name}")
    script = r'''
on run argv
    set listName to item 1 of argv
    set todoTitle to item 2 of argv
    set dateValue to item 3 of argv
    tell application "Reminders"
        set targetList to list listName
        if dateValue is "" then
            set createdReminder to make new reminder at end of reminders of targetList with properties {name:todoTitle}
        else
            set eventYear to item 4 of argv as integer
            set eventMonth to item 5 of argv as integer
            set eventDay to item 6 of argv as integer
            set dueDate to current date
            set year of dueDate to eventYear
            set month of dueDate to eventMonth
            set day of dueDate to eventDay
            set time of dueDate to 0
            set createdReminder to make new reminder at end of reminders of targetList with properties {name:todoTitle, due date:dueDate}
        end if
        return id of createdReminder
    end tell
end run
'''
    return run_osascript(
        script,
        [
            list_name,
            title,
            action_date or "",
            str(parsed_date.year) if parsed_date else "0",
            str(parsed_date.month) if parsed_date else "0",
            str(parsed_date.day) if parsed_date else "0",
        ],
    )


def add_reminder_todo(list_name: str, title: str, action_date: str) -> str:
    validate_iso_date(action_date)
    return add_reminder_item(list_name, title, action_date)


def create_reminder(
    list_name: str,
    title: str,
    action_date: str | None,
) -> dict[str, Any]:
    normalized_title = " ".join(title.split())
    identifier = add_reminder_item(list_name, normalized_title, action_date)
    audit_event(
        "added",
        "reminder",
        normalized_title,
        {"list": list_name, "date": action_date},
    )
    return {
        "id": identifier,
        "title": normalized_title,
        "list": list_name,
        "date": action_date,
        "status": "open",
    }


def list_reminders(vault: Path, list_name: str) -> list[dict[str, Any]]:
    if list_name not in reminder_list_names():
        raise CommandCenterError(f"Unknown macOS Reminders list: {list_name}")
    script = APPLE_SCRIPT_HELPERS + r'''
on run argv
    set listName to item 1 of argv
    set output to {}
    tell application "Reminders"
        set targetList to list listName
        set openReminders to every reminder of targetList whose completed is false
        repeat with reminderItem in openReminders
            try
                set dueValue to due date of reminderItem
                if dueValue is missing value then
                    set dueText to ""
                else
                    set dueText to my isoDate(dueValue)
                end if
            on error
                set dueText to ""
            end try
            set reminderLine to my cleanText(id of reminderItem) & tab & my cleanText(name of reminderItem) & tab & dueText
            set end of output to reminderLine
        end repeat
    end tell
    set AppleScript's text item delimiters to linefeed
    return output as text
end run
'''
    reminders = parse_tabular_output(
        run_osascript(script, [list_name]),
        ["id", "title", "due"],
    )
    task_by_uid = {
        task.calendar_uid: task
        for task in parse_tasks(vault / TASKS_RELATIVE_PATH)
        if task.calendar_uid
    }
    for reminder in reminders:
        task = task_by_uid.get(reminder["id"])
        reminder["list"] = list_name
        reminder["managed_task"] = task is not None
        reminder["task_date"] = task.action_date if task else None
    reminders.sort(
        key=lambda reminder: (
            reminder["due"] or "9999-12-31",
            reminder["title"].casefold(),
        )
    )
    return reminders


def complete_reminder(
    vault: Path,
    list_name: str,
    reminder_id: str,
) -> dict[str, Any]:
    matches = [
        task
        for task in parse_tasks(vault / TASKS_RELATIVE_PATH)
        if task.calendar_uid == reminder_id and not task.completed
    ]
    if len(matches) > 1:
        raise CommandCenterError("Multiple tasks share the same Reminder ID.")
    if matches:
        task = matches[0]
        return {
            "provider": "task",
            **complete_task(vault, task.title, task.action_date),
        }
    script = r'''
on run argv
    set listName to item 1 of argv
    set reminderId to item 2 of argv
    tell application "Reminders"
        set targetList to list listName
        set matches to every reminder of targetList whose id is reminderId
        if (count of matches) is 0 then error "Reminder not found"
        set targetReminder to item 1 of matches
        set reminderTitle to name of targetReminder
        set completed of targetReminder to true
        return reminderTitle
    end tell
end run
'''
    title = run_osascript(script, [list_name, reminder_id])
    audit_event(
        "completed",
        "reminder",
        title,
        {"list": list_name},
    )
    return {
        "provider": "reminders",
        "id": reminder_id,
        "title": title,
        "status": "completed",
    }


def update_reminder_todo(
    list_name: str,
    reminder_id: str,
    *,
    title: str,
    action_date: str | None = None,
    completed: bool,
) -> None:
    parsed_date = date.fromisoformat(action_date) if action_date else None
    script = r'''
on run argv
    set listName to item 1 of argv
    set reminderId to item 2 of argv
    set todoTitle to item 3 of argv
    set completionState to item 4 of argv
    set dateValue to item 5 of argv
    tell application "Reminders"
        set targetList to list listName
        set matches to every reminder of targetList whose id is reminderId
        if (count of matches) is 0 then error "Synced reminder not found"
        set targetReminder to item 1 of matches
        set name of targetReminder to todoTitle
        set completed of targetReminder to (completionState is "true")
        if dateValue is not "" then
            set eventYear to item 6 of argv as integer
            set eventMonth to item 7 of argv as integer
            set eventDay to item 8 of argv as integer
            set dueDate to current date
            set year of dueDate to eventYear
            set month of dueDate to eventMonth
            set day of dueDate to eventDay
            set time of dueDate to 0
            set due date of targetReminder to dueDate
        end if
    end tell
end run
'''
    run_osascript(
        script,
        [
            list_name,
            reminder_id,
            title,
            "true" if completed else "false",
            action_date or "",
            str(parsed_date.year if parsed_date else 0),
            str(parsed_date.month if parsed_date else 0),
            str(parsed_date.day if parsed_date else 0),
        ],
    )


def update_reminder(
    vault: Path,
    list_name: str,
    reminder_id: str,
    new_title: str,
    new_date: str,
) -> dict[str, Any]:
    validate_iso_date(new_date)
    new_title = " ".join(new_title.split())
    if not new_title:
        raise CommandCenterError("Reminder title cannot be empty.")
    matches = [
        task
        for task in parse_tasks(vault / TASKS_RELATIVE_PATH)
        if task.calendar_uid == reminder_id and not task.completed
    ]
    if len(matches) > 1:
        raise CommandCenterError("Multiple tasks share the same Reminder ID.")
    if matches:
        task = matches[0]
        return {
            "provider": "task",
            **update_task(
                vault,
                task.title,
                task.action_date or new_date,
                new_title,
                new_date,
            ),
        }
    current = next(
        (
            reminder
            for reminder in list_reminders(vault, list_name)
            if reminder["id"] == reminder_id
        ),
        None,
    )
    if current is None:
        raise CommandCenterError("Reminder not found.")
    update_reminder_todo(
        list_name,
        reminder_id,
        title=new_title,
        action_date=new_date,
        completed=False,
    )
    audit_event(
        "updated",
        "reminder",
        new_title,
        {
            "old_title": current["title"],
            "from_date": current["due"][:10] if current["due"] else None,
            "to_date": new_date,
            "list": list_name,
        },
    )
    return {
        "provider": "reminders",
        "id": reminder_id,
        "title": new_title,
        "date": new_date,
    }


def add_calendar_todo(calendar: str, title: str, action_date: str) -> str:
    validate_iso_date(action_date)
    if calendar not in calendar_names():
        raise CommandCenterError(f"Unknown macOS calendar: {calendar}")
    parsed_date = date.fromisoformat(action_date)
    calendar_ref = uuid.uuid4().hex
    script = r'''
on run argv
    set calendarName to item 1 of argv
    set todoTitle to item 2 of argv
    set calendarRef to item 3 of argv
    set eventYear to item 4 of argv as integer
    set eventMonth to item 5 of argv as integer
    set eventDay to item 6 of argv as integer

    set eventStart to current date
    set year of eventStart to eventYear
    set month of eventStart to eventMonth
    set day of eventStart to eventDay
    set time of eventStart to 0
    set eventEnd to eventStart + (1 * days)

    tell application "Calendar"
        set targetCalendar to calendar calendarName
        make new event at end of events of targetCalendar with properties {summary:"☐ " & todoTitle, description:"Command Center todo" & linefeed & "Ref: " & calendarRef, start date:eventStart, end date:eventEnd, allday event:true}
    end tell
end run
'''
    run_osascript(
        script,
        [
            calendar,
            title,
            calendar_ref,
            str(parsed_date.year),
            str(parsed_date.month),
            str(parsed_date.day),
        ],
    )
    return calendar_ref


def update_calendar_todo(
    calendar: str,
    uid: str,
    *,
    title: str,
    action_date: str | None = None,
    completed: bool,
) -> None:
    parsed_date = date.fromisoformat(action_date) if action_date else None
    script = r'''
on run argv
    set calendarName to item 1 of argv
    set calendarRef to item 2 of argv
    set todoTitle to item 3 of argv
    set completionState to item 4 of argv
    set dateValue to item 5 of argv

    tell application "Calendar"
        set targetCalendar to calendar calendarName
        set matchingEvents to every event of targetCalendar whose description contains ("Ref: " & calendarRef)
        if (count of matchingEvents) is 0 then error "Calendar todo event not found"
        set targetEvent to item 1 of matchingEvents
        if completionState is "true" then
            set summary of targetEvent to "✓ " & todoTitle
        else
            set summary of targetEvent to "☐ " & todoTitle
        end if
        if dateValue is not "" then
            set eventYear to item 6 of argv as integer
            set eventMonth to item 7 of argv as integer
            set eventDay to item 8 of argv as integer
            set eventStart to current date
            set year of eventStart to eventYear
            set month of eventStart to eventMonth
            set day of eventStart to eventDay
            set time of eventStart to 0
            set start date of targetEvent to eventStart
            set end date of targetEvent to eventStart + (1 * days)
            set allday event of targetEvent to true
        end if
    end tell
end run
'''
    arguments = [
        calendar,
        uid,
        title,
        "true" if completed else "false",
        action_date or "",
        str(parsed_date.year if parsed_date else 0),
        str(parsed_date.month if parsed_date else 0),
        str(parsed_date.day if parsed_date else 0),
    ]
    run_osascript(script, arguments)


def add_calendar_event(
    calendar: str,
    title: str,
    start: str,
    duration: int,
) -> dict[str, Any]:
    try:
        parsed_start = datetime.fromisoformat(start)
    except ValueError as exc:
        raise CommandCenterError(
            f"Invalid start '{start}'. Use YYYY-MM-DDTHH:MM."
        ) from exc
    if parsed_start.tzinfo is not None:
        raise CommandCenterError("Calendar start must be local time without a timezone.")
    if duration <= 0 or duration > 1440:
        raise CommandCenterError("Calendar duration must be between 1 and 1440 minutes.")
    if calendar not in calendar_names():
        raise CommandCenterError(f"Unknown macOS calendar: {calendar}")

    script = r'''
on run argv
    set calendarName to item 1 of argv
    set eventTitle to item 2 of argv
    set eventYear to item 3 of argv as integer
    set eventMonth to item 4 of argv as integer
    set eventDay to item 5 of argv as integer
    set eventHour to item 6 of argv as integer
    set eventMinute to item 7 of argv as integer
    set eventDuration to item 8 of argv as integer

    set eventStart to current date
    set year of eventStart to eventYear
    set month of eventStart to eventMonth
    set day of eventStart to eventDay
    set time of eventStart to (eventHour * hours) + (eventMinute * minutes)
    set eventEnd to eventStart + (eventDuration * minutes)

    tell application "Calendar"
        set targetCalendar to calendar calendarName
        set createdEvent to make new event at end of events of targetCalendar with properties {summary:eventTitle, start date:eventStart, end date:eventEnd}
        return uid of createdEvent
    end tell
end run
'''
    uid = run_osascript(
        script,
        [
            calendar,
            title,
            str(parsed_start.year),
            str(parsed_start.month),
            str(parsed_start.day),
            str(parsed_start.hour),
            str(parsed_start.minute),
            str(duration),
        ],
    )
    audit_event(
        "added",
        "calendar-event",
        title,
        {"calendar": calendar, "start": start, "duration_minutes": duration},
    )
    return {
        "calendar": calendar,
        "title": title,
        "start": start,
        "duration_minutes": duration,
        "uid": uid,
    }


def mail_attention(
    query: str | None,
    unread_only: bool = False,
    account: str | None = None,
) -> list[dict[str, str]]:
    script = APPLE_SCRIPT_HELPERS + r'''
on run argv
    set searchQuery to ""
    if (count of argv) > 0 then set searchQuery to item 1 of argv
    set unreadOnly to false
    if (count of argv) > 1 then set unreadOnly to (item 2 of argv is "true")
    set accountAddress to ""
    if (count of argv) > 2 then set accountAddress to item 3 of argv
    set cutoffDate to (current date) - (48 * hours)
    set output to {}
    tell application "Mail"
        if accountAddress is not "" then
            set matchingMessages to {}
            set accountFound to false
            repeat with acct in accounts
                if (email addresses of acct) contains accountAddress then
                    set accountFound to true
                    repeat with box in mailboxes of acct
                        if (name of box as text) is "Inbox" or (name of box as text) is "INBOX" then
                            if unreadOnly then
                                set matchingMessages to matchingMessages & (every message of box whose read status is false)
                            else
                                set matchingMessages to matchingMessages & (every message of box whose date received > cutoffDate)
                            end if
                        end if
                    end repeat
                end if
            end repeat
            if accountFound is false then error "Mail account not found"
        else if searchQuery is "" then
            set matchingMessages to every message of inbox whose ((read status is false and date received > cutoffDate) or flagged status is true)
        else if unreadOnly then
            set matchingMessages to every message of inbox whose (read status is false and (subject contains searchQuery or sender contains searchQuery))
        else
            set matchingMessages to every message of inbox whose (subject contains searchQuery or sender contains searchQuery)
        end if
        set itemCount to count of matchingMessages
        if itemCount > 100 then set itemCount to 100
        repeat with i from 1 to itemCount
            set msg to item i of matchingMessages
            try
                set stableId to message id of msg as text
            on error
                set stableId to ""
            end try
            set messageLine to my cleanText(sender of msg) & tab & my cleanText(subject of msg) & tab & my isoDate(date received of msg) & tab & (read status of msg as text) & tab & (flagged status of msg as text) & tab & my cleanText(stableId)
            set end of output to messageLine
        end repeat
    end tell
    set AppleScript's text item delimiters to linefeed
    return output as text
end run
'''
    messages = parse_tabular_output(
        run_osascript(
            script,
            [
                query or "",
                "true" if unread_only else "false",
                account or "",
            ],
        ),
        ["sender", "subject", "received", "read", "flagged", "message_id"],
    )
    messages.sort(key=lambda message: message["received"], reverse=True)
    return messages[: 30 if query else 10]


def parse_health_check(entry: str) -> tuple[str, str]:
    if "|" not in entry:
        raise CommandCenterError(
            f"Invalid health check '{entry}'. Use 'Label|https://url'."
        )
    label, url = (part.strip() for part in entry.split("|", 1))
    parsed = urllib.parse.urlparse(url)
    if (
        not label
        or parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise CommandCenterError(
            f"Invalid health check '{entry}'. Use 'Label|https://url'."
        )
    validate_public_hostname(parsed.hostname)
    return label, url


def validate_public_hostname(hostname: str) -> None:
    if hostname.casefold() == "localhost" or hostname.casefold().endswith(".localhost"):
        raise CommandCenterError("Health checks must use a public host.")
    try:
        addresses = {
            ipaddress.ip_address(item[4][0])
            for item in socket.getaddrinfo(hostname, None)
        }
    except socket.gaierror as exc:
        raise IntegrationError(f"Health host cannot be resolved: {hostname}") from exc
    if not addresses or any(not address.is_global for address in addresses):
        raise CommandCenterError("Health checks must use public IP addresses.")


def check_health(entry: str) -> dict[str, Any]:
    label, url = parse_health_check(entry)
    started = time.monotonic()
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "CommandCenter/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status_code = response.status
            response.read(256)
        error = None
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        error = f"http_{exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        status_code = None
        error = type(exc).__name__.lower()
    elapsed_ms = round((time.monotonic() - started) * 1000)
    return {
        "label": label,
        "url": url,
        "up": status_code is not None and 200 <= status_code < 400,
        "status_code": status_code,
        "latency_ms": elapsed_ms,
        "error": error,
    }


def safe_health_job(job: tuple[str, str]) -> dict[str, Any]:
    project_name, entry = job
    try:
        return {"project": project_name, **check_health(entry)}
    except CommandCenterError as exc:
        return {
            "project": project_name,
            "label": entry.split("|", 1)[0].strip() or "invalid",
            "url": entry.split("|", 1)[1].strip() if "|" in entry else None,
            "up": False,
            "status_code": None,
            "latency_ms": None,
            "error": str(exc),
        }


def project_health(vault: Path, name: str | None = None) -> list[dict[str, Any]]:
    projects = (
        [project_by_name(vault, name)]
        if name
        else [
            project
            for project in load_projects(vault)
            if project.status == "active" and project.health_checks
        ]
    )
    jobs = [
        (project.name, entry)
        for project in projects
        for entry in project.health_checks
    ]
    if not jobs:
        return []

    with ThreadPoolExecutor(max_workers=min(8, len(jobs))) as pool:
        return list(pool.map(safe_health_job, jobs))


def ensure_inbox_file(vault: Path) -> Path:
    path = vault / INBOX_RELATIVE_PATH
    if not path.exists():
        atomic_write(path, "# Inbox\n\n")
    return path


def capture_note(
    vault: Path,
    text: str,
    source: str,
    project: str | None,
) -> dict[str, Any]:
    normalized_text, normalized_source = validate_project_memory(text, source)
    project_name = project_by_name(vault, project).name if project else None
    now = datetime.now().astimezone()
    record_id = f"{now.strftime('%Y%m%dT%H%M%S%z')}-{uuid.uuid4().hex[:6]}"
    lines = [
        f"### {now.strftime('%Y-%m-%d %H:%M:%S')}",
        f"<!-- id: {record_id} -->",
        normalized_text,
        "",
        f"- Πηγή: {normalized_source}",
    ]
    if project_name:
        lines.append(f"- Project: [[Projects/{project_name}|{project_name}]]")
    lines.append("")
    inbox = vault / INBOX_RELATIVE_PATH
    with path_lock(inbox):
        inbox = ensure_inbox_file(vault)
        atomic_write(
            inbox,
            inbox.read_text(encoding="utf-8").rstrip()
            + "\n\n"
            + "\n".join(lines),
        )
    return {
        "id": record_id,
        "text": normalized_text,
        "source": normalized_source,
        "project": project_name,
        "created_at": now.isoformat(timespec="seconds"),
    }


def inbox_items(vault: Path) -> list[dict[str, Any]]:
    path = vault / INBOX_RELATIVE_PATH
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    items: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        if not lines[index].startswith("### "):
            index += 1
            continue
        created_at = lines[index].removeprefix("### ").strip()
        block_end = index + 1
        while block_end < len(lines) and not lines[block_end].startswith("### "):
            block_end += 1
        block = lines[index + 1 : block_end]
        record_id = ""
        source = ""
        project = None
        body: list[str] = []
        for line in block:
            id_match = RECORD_ID_PATTERN.match(line)
            if id_match:
                record_id = id_match.group("id")
            elif line.startswith("- Πηγή: "):
                source = line.removeprefix("- Πηγή: ").strip()
            elif line.startswith("- Project: "):
                project = line.removeprefix("- Project: ").strip()
            elif line.strip():
                body.append(line.strip())
        items.append(
            {
                "id": record_id,
                "created_at": created_at,
                "text": " ".join(body),
                "source": source,
                "project": project,
            }
        )
        index = block_end
    return items


def ensure_waiting_on_file(vault: Path) -> Path:
    path = vault / WAITING_ON_RELATIVE_PATH
    if not path.exists():
        atomic_write(path, "# Waiting on\n\n")
    return path


def parse_waiting_on(vault: Path) -> list[WaitingOnItem]:
    path = vault / WAITING_ON_RELATIVE_PATH
    if not path.is_file():
        return []
    items: list[WaitingOnItem] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        match = WAITING_ITEM_PATTERN.match(line)
        if not match:
            continue
        try:
            metadata = json.loads(match.group("metadata"))
        except json.JSONDecodeError as exc:
            raise CommandCenterError(
                f"Malformed Waiting-on metadata on line {index + 1}."
            ) from exc
        items.append(
            WaitingOnItem(
                id=str(metadata["id"]),
                person=match.group("person").strip(),
                item=match.group("item").strip(),
                due_date=metadata.get("due"),
                completed=match.group("state").lower() == "x",
                line_number=index + 1,
            )
        )
    return items


def add_waiting_on(
    vault: Path,
    person: str,
    item: str,
    due_date: str | None,
) -> dict[str, Any]:
    person = " ".join(person.split())
    item = " ".join(item.split())
    if not person or not item:
        raise CommandCenterError("Waiting-on person and item are required.")
    validate_project_memory(person, "Χρήστης (chat)")
    validate_project_memory(item, "Χρήστης (chat)")
    if due_date:
        validate_iso_date(due_date)
    record_id = f"waiting-{uuid.uuid4().hex[:10]}"
    metadata = {"id": record_id}
    if due_date:
        metadata["due"] = due_date
    line = (
        f"- [ ] {person} — {item} "
        f"<!-- cc: {json.dumps(metadata, ensure_ascii=False, sort_keys=True)} -->"
    )
    path = vault / WAITING_ON_RELATIVE_PATH
    with path_lock(path):
        path = ensure_waiting_on_file(vault)
        atomic_write(path, path.read_text(encoding="utf-8").rstrip() + "\n" + line + "\n")
    return {
        "id": record_id,
        "person": person,
        "item": item,
        "due_date": due_date,
        "completed": False,
    }


def list_waiting_on(vault: Path, include_completed: bool) -> list[dict[str, Any]]:
    today = date.today().isoformat()
    items = [
        asdict(item)
        for item in parse_waiting_on(vault)
        if include_completed or not item.completed
    ]
    for item in items:
        item["overdue"] = bool(
            item["due_date"] and not item["completed"] and item["due_date"] < today
        )
    return items


def complete_waiting_on(vault: Path, query: str) -> dict[str, Any]:
    normalized = " ".join(query.split()).casefold()
    matches = [
        item
        for item in parse_waiting_on(vault)
        if not item.completed
        and (
            normalized == item.item.casefold()
            or normalized in item.item.casefold()
            or normalized == item.person.casefold()
        )
    ]
    if not matches:
        raise CommandCenterError(f"No open Waiting-on item matches: {query}")
    if len(matches) > 1:
        raise CommandCenterError(
            f"Multiple open Waiting-on items match: {query}",
            [asdict(item) for item in matches],
        )
    item = matches[0]
    path = vault / WAITING_ON_RELATIVE_PATH
    with path_lock(path):
        lines = path.read_text(encoding="utf-8").splitlines()
        line = lines[item.line_number - 1]
        lines[item.line_number - 1] = line.replace("- [ ] ", "- [x] ", 1)
        atomic_write(path, "\n".join(lines).rstrip() + "\n")
    return asdict(item) | {"completed": True}


def ensure_learning_file(vault: Path) -> Path:
    path = vault / LEARNING_RELATIVE_PATH
    if not path.exists():
        sections = "\n\n".join(f"## {label}" for label in LEARNING_KINDS.values())
        atomic_write(path, f"# Learning\n\n{sections}\n")
    return path


def parse_learning(vault: Path) -> list[LearningItem]:
    path = vault / LEARNING_RELATIVE_PATH
    if not path.is_file():
        return []
    items: list[LearningItem] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        match = LEARNING_ITEM_PATTERN.match(line)
        if not match:
            continue
        try:
            metadata = json.loads(match.group("metadata"))
        except json.JSONDecodeError as exc:
            raise CommandCenterError(
                f"Malformed Learning metadata on line {index + 1}."
            ) from exc
        display_title = match.group("title").strip()
        markdown_link = re.match(r"^\[(?P<title>.+)\]\(.+\)$", display_title)
        items.append(
            LearningItem(
                id=str(metadata["id"]),
                title=markdown_link.group("title")
                if markdown_link
                else display_title,
                kind=str(metadata["kind"]),
                url=metadata.get("url"),
                project=metadata.get("project"),
                source=str(metadata.get("source") or ""),
                added=str(metadata["added"]),
                completed=match.group("state").lower() == "x",
                line_number=index + 1,
            )
        )
    return items


def add_learning(
    vault: Path,
    title: str,
    kind: str,
    url: str | None,
    project: str | None,
    source: str,
) -> dict[str, Any]:
    normalized_title, normalized_source = validate_project_memory(title, source)
    project_name = project_by_name(vault, project).name if project else None
    if url and not re.match(r"^https?://", url):
        raise CommandCenterError("Learning URL must start with http:// or https://.")
    if url and (
        SENSITIVE_VALUE_PATTERN.search(url)
        or SENSITIVE_SHAPE_PATTERN.search(url)
    ):
        raise CommandCenterError("Learning URL cannot contain credential-like values.")
    metadata = {
        "id": uuid.uuid4().hex[:12],
        "kind": kind,
        "url": url,
        "project": project_name,
        "source": normalized_source,
        "added": date.today().isoformat(),
    }
    display_title = (
        f"[{normalized_title}]({url})" if url else normalized_title
    )
    line = (
        f"- [ ] {display_title} "
        f"<!-- cc: {json.dumps(metadata, ensure_ascii=False, separators=(',', ':'))} -->"
    )
    learning = vault / LEARNING_RELATIVE_PATH
    with path_lock(learning):
        learning = ensure_learning_file(vault)
        ensure_task_section(learning, LEARNING_KINDS[kind])
        append_task(learning, LEARNING_KINDS[kind], line)
    audit_event(
        "added",
        "learning",
        normalized_title,
        {"kind": kind, "project": project_name},
    )
    return metadata | {"title": normalized_title}


def list_learning(
    vault: Path,
    kind: str | None,
    project: str | None,
    include_done: bool,
) -> list[dict[str, Any]]:
    items = parse_learning(vault)
    filtered = [
        item
        for item in items
        if (include_done or not item.completed)
        and (kind is None or item.kind == kind)
        and (
            project is None
            or (item.project or "").casefold() == project.casefold()
        )
    ]
    return [asdict(item) for item in filtered]


def complete_learning(vault: Path, query: str) -> dict[str, Any]:
    path = vault / LEARNING_RELATIVE_PATH
    normalized = query.casefold().strip()
    with path_lock(path):
        matches = [
            item
            for item in parse_learning(vault)
            if not item.completed
            and (
                item.id == query
                or normalized in item.title.casefold()
            )
        ]
        if not matches:
            raise CommandCenterError(f"No learning item matches: {query}")
        if len(matches) > 1:
            raise CommandCenterError(
                f"Multiple learning items match: {query}",
                [asdict(item) for item in matches],
            )
        item = matches[0]
        lines = path.read_text(encoding="utf-8").splitlines()
        line_index = item.line_number - 1
        lines[line_index] = lines[line_index].replace("- [ ]", "- [x]", 1)
        atomic_write(path, "\n".join(lines).rstrip() + "\n")
    audit_event(
        "completed",
        "learning",
        item.title,
        {"kind": item.kind, "project": item.project},
    )
    return {"id": item.id, "title": item.title, "status": "completed"}


def work_daily_root(vault: Path) -> Path:
    return vault / WORK_RELATIVE_PATH / "Daily Notes"


def work_daily_path(vault: Path, task_date: date) -> Path:
    month_folder = f"{task_date.month}. {MONTH_NAMES[task_date.month - 1]} {task_date.year}"
    return work_daily_root(vault) / month_folder / f"{task_date.isoformat()}.md"


def personal_daily_path(vault: Path, task_date: date) -> Path:
    month_folder = f"{task_date.month}. {MONTH_NAMES[task_date.month - 1]} {task_date.year}"
    return (
        vault
        / PERSONAL_DAILY_RELATIVE_PATH
        / month_folder
        / f"{task_date.isoformat()}.md"
    )


def section_uses_personal_daily(vault: Path, section: str) -> bool:
    if section.casefold() == "personal":
        return True
    return any(
        project.name.casefold() == section.casefold()
        and project.area == "personal"
        for project in load_projects(vault)
    )


def open_daily_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    entries = daily_task_entries(path)
    open_paths = {
        entry["path_key"]
        for entry in entries
        if not entry["completed"] and not entry["deleted"]
    }
    carried: list[str] = []
    seen: set[tuple[str, ...]] = set()
    for entry in entries:
        has_open_descendant = any(
            len(path_key) > len(entry["path_key"])
            and path_key[: len(entry["path_key"])] == entry["path_key"]
            for path_key in open_paths
        )
        if (
            entry["deleted"]
            or (entry["completed"] and not has_open_descendant)
            or entry["path_key"] in seen
        ):
            continue
        line = entry["raw"]
        if entry["completed"]:
            line = re.sub(r"\[[xX]\]", "[ ]", line, count=1)
        carried.append(line)
        seen.add(entry["path_key"])
    return carried


def daily_line_identity(line: str) -> str | None:
    match = DAILY_TASK_PATTERN.match(line)
    if not match:
        return None
    title = CALENDAR_METADATA_PATTERN.sub("", match.group("title")).strip()
    return title.casefold()


def merge_daily_lines(
    path: Path,
    carried_lines: list[str],
    *,
    personal: bool,
) -> int:
    if not carried_lines:
        return 0
    with path_lock(path):
        lines = path.read_text(encoding="utf-8").splitlines()
        existing = {
            identity
            for line in lines
            if (identity := daily_line_identity(line))
        }
        inserted = 0
        for carried_index, carried_line in enumerate(carried_lines):
            identity = daily_line_identity(carried_line)
            if not identity or identity in existing:
                continue
            carried_indent = (
                len(carried_line) - len(carried_line.lstrip(" \t"))
            )
            insertion = None
            for previous_line in reversed(carried_lines[:carried_index]):
                previous_identity = daily_line_identity(previous_line)
                if not previous_identity or previous_identity not in existing:
                    continue
                previous_index = next(
                    (
                        index
                        for index, line in enumerate(lines)
                        if daily_line_identity(line) == previous_identity
                    ),
                    None,
                )
                if previous_index is None:
                    continue
                previous_indent = (
                    len(lines[previous_index])
                    - len(lines[previous_index].lstrip(" \t"))
                )
                insertion = previous_index + 1
                if carried_indent <= previous_indent:
                    while insertion < len(lines):
                        candidate = DAILY_TASK_PATTERN.match(lines[insertion])
                        if candidate:
                            indent = (
                                len(lines[insertion])
                                - len(lines[insertion].lstrip(" \t"))
                            )
                            if indent <= previous_indent:
                                break
                        insertion += 1
                break
            if insertion is None:
                insertion = (
                    2
                    if personal and lines and lines[0].startswith("# ")
                    else next(
                        (
                            index
                            for index, line in enumerate(lines)
                            if line == "## Command Center"
                        ),
                        len(lines),
                    )
                )
            lines.insert(insertion, carried_line)
            existing.add(identity)
            inserted += 1
        if not inserted:
            return 0
        atomic_write(path, "\n".join(lines).rstrip() + "\n")
    return inserted


def daily_task_entries(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    entries: list[dict[str, Any]] = []
    hierarchy: list[tuple[int, str]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        match = DAILY_TASK_PATTERN.match(line)
        if not match:
            continue
        indent = len(line) - len(line.lstrip(" \t"))
        while hierarchy and indent <= hierarchy[-1][0]:
            hierarchy.pop()
        title = CALENDAR_METADATA_PATTERN.sub(
            "",
            match.group("title"),
        ).strip()
        deleted = title.endswith("→ διαγράφηκε")
        title = re.sub(
            r"\s+→\s+(?:μεταφέρθηκε\s+\d{4}-\d{2}-\d{2}|διαγράφηκε)$",
            "",
            title,
        )
        path_key = tuple([*(title for _, title in hierarchy), title])
        entries.append(
            {
                "line_number": index + 1,
                "title": title,
                "path_key": path_key,
                "completed": match.group("state").lower() == "x",
                "deleted": deleted,
                "raw": line,
            }
        )
        hierarchy.append((indent, title))
    return entries


def remove_completed_carryovers(source: Path, target: Path) -> int:
    if not source.is_file() or not target.is_file():
        return 0
    source_entries = daily_task_entries(source)
    open_paths = {
        entry["path_key"]
        for entry in source_entries
        if not entry["completed"] and not entry["deleted"]
    }
    completed_paths = {
        entry["path_key"]
        for entry in source_entries
        if entry["completed"]
        and not any(
            len(path_key) > len(entry["path_key"])
            and path_key[: len(entry["path_key"])] == entry["path_key"]
            for path_key in open_paths
        )
    }
    removable = [
        entry["line_number"]
        for entry in daily_task_entries(target)
        if not entry["completed"] and entry["path_key"] in completed_paths
    ]
    if not removable:
        return 0
    with path_lock(target):
        lines = target.read_text(encoding="utf-8").splitlines()
        for line_number in sorted(removable, reverse=True):
            lines.pop(line_number - 1)
        atomic_write(target, "\n".join(lines).rstrip() + "\n")
    return len(removable)


def ensure_personal_daily_file(vault: Path, target_date: date) -> tuple[Path, bool]:
    path = personal_daily_path(vault, target_date)
    with path_lock(path):
        if path.exists():
            return path, False
        previous = personal_daily_path(vault, target_date - timedelta(days=1))
        lines = open_daily_lines(previous)
        content = f"# Personal daily tasks — {target_date.isoformat()}\n\n"
        content += "\n".join(lines) + ("\n" if lines else "")
        atomic_write(path, content)
    return path, True


def append_personal_daily_task(
    vault: Path,
    title: str,
    target_date: str,
    parent_line: int | None = None,
) -> str:
    parsed_date = date.fromisoformat(target_date)
    path, _ = ensure_personal_daily_file(vault, parsed_date)
    with path_lock(path):
        lines = path.read_text(encoding="utf-8").splitlines()
        exists = any(
            match.group("state").lower() != "x"
            and match.group("title").strip().casefold() == title.casefold()
            for line in lines
            if (match := DAILY_TASK_PATTERN.match(line))
        )
        if not exists:
            new_line = f"- [ ] {title}"
            if parent_line is None:
                lines.append(new_line)
            else:
                parent_index = parent_line - 1
                if parent_index < 0 or parent_index >= len(lines):
                    raise CommandCenterError("Personal parent line is out of range.")
                parent_match = DAILY_TASK_PATTERN.match(lines[parent_index])
                if (
                    not parent_match
                    or parent_match.group("state").lower() == "x"
                ):
                    raise CommandCenterError(
                        "Personal parent must be an open daily task."
                    )
                parent_indent = (
                    len(lines[parent_index])
                    - len(lines[parent_index].lstrip(" \t"))
                )
                insertion = parent_index + 1
                while insertion < len(lines):
                    candidate = DAILY_TASK_PATTERN.match(lines[insertion])
                    if candidate:
                        indent = (
                            len(lines[insertion])
                            - len(lines[insertion].lstrip(" \t"))
                        )
                        if indent <= parent_indent:
                            break
                    insertion += 1
                leading = lines[parent_index][
                    : len(lines[parent_index])
                    - len(lines[parent_index].lstrip(" \t"))
                ]
                lines.insert(insertion, f"{leading}\t- [ ] {title}")
            atomic_write(path, "\n".join(lines).rstrip() + "\n")
    return str(path.relative_to(vault))


def complete_personal_daily_task(
    vault: Path,
    title: str,
    target_date: str,
    moved_to: str | None = None,
) -> bool:
    path = personal_daily_path(vault, date.fromisoformat(target_date))
    if not path.is_file():
        return False
    with path_lock(path):
        lines = path.read_text(encoding="utf-8").splitlines()
        matches = [
            index
            for index, line in enumerate(lines)
            if (match := DAILY_TASK_PATTERN.match(line))
            and match.group("state").lower() != "x"
            and match.group("title").strip().casefold() == title.casefold()
        ]
        if len(matches) > 1:
            raise CommandCenterError(
                f"Multiple Personal daily tasks match exactly: {title}"
            )
        if not matches:
            return False
        index = matches[0]
        match = DAILY_TASK_PATTERN.match(lines[index])
        if match is None:
            raise CommandCenterError("Personal daily task changed while selected.")
        suffix = f" → μεταφέρθηκε {moved_to}" if moved_to else ""
        lines[index] = f"{match.group('prefix')}[x] {title}{suffix}"
        atomic_write(path, "\n".join(lines).rstrip() + "\n")
    return True


def reopen_personal_daily_task(
    vault: Path,
    title: str,
    target_date: str,
) -> bool:
    path = personal_daily_path(vault, date.fromisoformat(target_date))
    if not path.is_file():
        return False
    with path_lock(path):
        lines = path.read_text(encoding="utf-8").splitlines()
        matches = [
            index
            for index, line in enumerate(lines)
            if (match := DAILY_TASK_PATTERN.match(line))
            and match.group("state").lower() == "x"
            and match.group("title").strip().casefold() == title.casefold()
        ]
        if len(matches) != 1:
            return False
        index = matches[0]
        match = DAILY_TASK_PATTERN.match(lines[index])
        if match is None:
            return False
        lines[index] = f"{match.group('prefix')}[ ] {title}"
        atomic_write(path, "\n".join(lines).rstrip() + "\n")
    return True


def delete_personal_daily_task(
    vault: Path,
    title: str,
    target_date: str,
) -> bool:
    path = personal_daily_path(vault, date.fromisoformat(target_date))
    if not path.is_file():
        return False
    with path_lock(path):
        lines = path.read_text(encoding="utf-8").splitlines()
        matches = [
            index
            for index, line in enumerate(lines)
            if (match := DAILY_TASK_PATTERN.match(line))
            and match.group("title").strip().casefold() == title.casefold()
        ]
        if len(matches) != 1:
            return False
        index = matches[0]
        match = DAILY_TASK_PATTERN.match(lines[index])
        if match is None:
            return False
        lines[index] = f"{match.group('prefix')}[x] {title} → διαγράφηκε"
        atomic_write(path, "\n".join(lines).rstrip() + "\n")
    return True


def move_personal_daily_task(
    vault: Path,
    title: str,
    previous_date: str,
    target_date: str,
) -> str:
    complete_personal_daily_task(
        vault,
        title,
        previous_date,
        moved_to=target_date,
    )
    return append_personal_daily_task(vault, title, target_date)


def update_personal_daily_task(
    vault: Path,
    old_title: str,
    old_date: str,
    new_title: str,
    new_date: str,
) -> str:
    if old_date != new_date:
        complete_personal_daily_task(
            vault,
            old_title,
            old_date,
            moved_to=new_date,
        )
        return append_personal_daily_task(vault, new_title, new_date)
    path = personal_daily_path(vault, date.fromisoformat(old_date))
    if not path.is_file():
        return append_personal_daily_task(vault, new_title, new_date)
    with path_lock(path):
        lines = path.read_text(encoding="utf-8").splitlines()
        matches = [
            index
            for index, line in enumerate(lines)
            if (match := DAILY_TASK_PATTERN.match(line))
            and match.group("state").lower() != "x"
            and match.group("title").strip().casefold() == old_title.casefold()
        ]
        if len(matches) != 1:
            raise CommandCenterError(
                f"Expected one Personal daily task matching: {old_title}"
            )
        index = matches[0]
        match = DAILY_TASK_PATTERN.match(lines[index])
        if match is None:
            raise CommandCenterError("Personal daily task changed while selected.")
        lines[index] = f"{match.group('prefix')}[ ] {new_title}"
        atomic_write(path, "\n".join(lines).rstrip() + "\n")
    return str(path.relative_to(vault))


def daily_rollover(vault: Path, target_date: str) -> dict[str, Any]:
    validate_iso_date(target_date)
    current = date.fromisoformat(target_date)
    previous = current - timedelta(days=1)
    personal_path = personal_daily_path(vault, current)
    work_path = work_daily_path(vault, current)
    created: dict[str, Any] = {"date": target_date, "created": []}

    personal_path, personal_created = ensure_personal_daily_file(vault, current)
    personal_carried = merge_daily_lines(
        personal_path,
        open_daily_lines(personal_daily_path(vault, previous)),
        personal=True,
    )
    personal_removed = remove_completed_carryovers(
        personal_daily_path(vault, previous),
        personal_path,
    )
    if personal_created:
        lines = open_daily_lines(personal_path)
        if not lines:
            for task in list_tasks(vault, "today", None):
                if task["section"].casefold() != "work":
                    append_personal_daily_task(
                        vault,
                        task["title"],
                        target_date,
                    )
            lines = open_daily_lines(personal_path)
        created["created"].append(
            {
                "area": "Personal",
                "path": str(personal_path.relative_to(vault)),
                "carried": len(lines),
            }
        )
    elif personal_carried or personal_removed:
        created["created"].append(
            {
                "area": "Personal",
                "path": str(personal_path.relative_to(vault)),
                "carried": personal_carried,
                "removed": personal_removed,
                "merged": True,
            }
        )

    work_created = not work_path.exists()
    if work_created:
        work_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(work_path, "")
    work_carried = merge_daily_lines(
        work_path,
        open_daily_lines(work_daily_path(vault, previous)),
        personal=False,
    )
    work_removed = remove_completed_carryovers(
        work_daily_path(vault, previous),
        work_path,
    )
    if work_created or work_carried or work_removed:
        created["created"].append(
            {
                "area": "Work",
                "path": str(work_path.relative_to(vault)),
                "carried": work_carried,
                "removed": work_removed,
                "merged": not work_created,
            }
        )
    return created


def list_daily_tasks(
    vault: Path,
    target_date: str,
    include_completed: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    validate_iso_date(target_date)
    current = date.fromisoformat(target_date)
    personal_path = personal_daily_path(vault, current)
    personal: list[dict[str, Any]] = []
    hierarchy: list[tuple[int, str]] = []
    if personal_path.is_file():
        for index, line in enumerate(
            personal_path.read_text(encoding="utf-8").splitlines()
        ):
            match = DAILY_TASK_PATTERN.match(line)
            if not match:
                continue
            indent = len(line) - len(line.lstrip(" \t"))
            while hierarchy and indent <= hierarchy[-1][0]:
                hierarchy.pop()
            title = match.group("title").strip()
            if title.endswith("→ διαγράφηκε"):
                continue
            completed = match.group("state").lower() == "x"
            if include_completed or not completed:
                personal.append(
                    {
                        "title": title,
                        "parent_path": [parent for _, parent in hierarchy],
                        "path": str(personal_path.relative_to(vault)),
                        "task_date": target_date,
                        "line_number": index + 1,
                        "completed": completed,
                    }
                )
            hierarchy.append((indent, title))
    work = [
        asdict(task)
        for task in parse_work_tasks(vault)
        if task.task_date == target_date
        and not task.title.endswith("→ διαγράφηκε")
        and (include_completed or not task.completed)
    ]
    return {"personal": personal, "work": work}


def next_work_task(vault: Path) -> dict[str, Any] | None:
    today = date.today().isoformat()
    tasks = [
        task
        for task in parse_work_tasks(vault)
        if not task.completed and task.task_date >= today
    ]
    tasks.sort(key=lambda task: (task.task_date, task.path, task.line_number))
    for task in tasks:
        child_path = [*task.parent_path, task.title]
        has_open_child = any(
            other.path == task.path
            and not other.completed
            and other.parent_path == child_path
            for other in tasks
        )
        if not has_open_child:
            return asdict(task)
    return None


def parse_work_tasks(vault: Path) -> list[WorkTask]:
    root = work_daily_root(vault)
    if not root.is_dir():
        return []
    tasks: list[WorkTask] = []
    for note in sorted(root.glob("*/*.md")):
        try:
            task_date = date.fromisoformat(note.stem).isoformat()
        except ValueError:
            continue
        lines = note.read_text(encoding="utf-8").splitlines()
        managed_bounds = markdown_section_bounds(lines, "Command Center")
        hierarchy: list[tuple[int, str]] = []
        for index, line in enumerate(lines):
            match = WORK_TASK_PATTERN.match(line)
            if not match:
                continue
            indent = len(line) - len(line.lstrip(" \t"))
            raw_title = match.group("title").strip()
            calendar_match = CALENDAR_METADATA_PATTERN.search(raw_title)
            calendar_data = (
                json.loads(calendar_match.group("metadata"))
                if calendar_match
                else {}
            )
            title = CALENDAR_METADATA_PATTERN.sub("", raw_title).strip()
            while hierarchy and indent <= hierarchy[-1][0]:
                hierarchy.pop()
            managed = bool(
                managed_bounds
                and managed_bounds[0] < index < managed_bounds[1]
            )
            tasks.append(
                WorkTask(
                    title=title,
                    parent_path=[parent for _, parent in hierarchy],
                    task_date=task_date,
                    path=str(note.relative_to(vault)),
                    line_number=index + 1,
                    completed=match.group("state").lower() == "x",
                    managed=managed,
                    sync_provider=calendar_data.get("provider", "calendar")
                    if calendar_data
                    else None,
                    calendar_name=calendar_data.get("name"),
                    calendar_uid=calendar_data.get("uid"),
                )
            )
            hierarchy.append((indent, title))
    return tasks


def add_work_task(
    vault: Path,
    title: str,
    task_date: str,
    parent_line: int | None = None,
) -> dict[str, Any]:
    validate_iso_date(task_date)
    normalized_title = " ".join(title.split())
    if not normalized_title or "\n" in title or "\r" in title:
        raise CommandCenterError("Work task title must fit on one non-empty line.")
    if parent_line is not None and parent_line < 1:
        raise CommandCenterError("Work parent line must be positive.")
    calendar_name = "Work"
    sync_provider = "calendar"
    calendar_uid = add_calendar_todo(
        calendar_name,
        normalized_title,
        task_date,
    )
    line = (
        f"- [ ] {normalized_title}"
        f"{calendar_metadata(calendar_name, calendar_uid, sync_provider)}"
    )
    note = work_daily_path(vault, date.fromisoformat(task_date))
    with path_lock(note):
        if note.exists():
            content = note.read_text(encoding="utf-8").rstrip()
        else:
            if parent_line is not None:
                raise CommandCenterError(
                    "Work parent line requires an existing Daily Note."
                )
            note.parent.mkdir(parents=True, exist_ok=True)
            content = ""
        if parent_line is None:
            atomic_write(
                note,
                append_line_to_section(content, "Command Center", line),
            )
        else:
            lines = content.splitlines()
            parent_index = parent_line - 1
            if parent_index < 0 or parent_index >= len(lines):
                raise CommandCenterError("Work parent line is out of range.")
            parent_match = WORK_TASK_PATTERN.match(lines[parent_index])
            if (
                not parent_match
                or parent_match.group("state").lower() == "x"
            ):
                raise CommandCenterError(
                    "Work parent must be an open daily task."
                )
            parent_indent = (
                len(lines[parent_index])
                - len(lines[parent_index].lstrip(" \t"))
            )
            insertion = parent_index + 1
            while insertion < len(lines):
                candidate = WORK_TASK_PATTERN.match(lines[insertion])
                if candidate:
                    indent = (
                        len(lines[insertion])
                        - len(lines[insertion].lstrip(" \t"))
                    )
                    if indent <= parent_indent:
                        break
                insertion += 1
            leading = lines[parent_index][
                : len(lines[parent_index])
                - len(lines[parent_index].lstrip(" \t"))
            ]
            nested_line = (
                f"{leading}\t- [ ] {normalized_title}"
                f"{calendar_metadata(calendar_name, calendar_uid, sync_provider)}"
            )
            lines.insert(insertion, nested_line)
            atomic_write(note, "\n".join(lines).rstrip() + "\n")
    audit_event(
        "added",
        "work-task",
        normalized_title,
        {"date": task_date, "parent_line": parent_line},
    )
    reconcile_next_day(vault, task_date)
    return {
        "title": normalized_title,
        "date": task_date,
        "path": str(note.relative_to(vault)),
        "calendar": calendar_name,
        "calendar_uid": calendar_uid,
        "sync_provider": sync_provider,
        "parent_line": parent_line,
    }


def complete_work_task(
    vault: Path, query: str, task_date: str | None = None
) -> dict[str, Any]:
    normalized = query.casefold().strip()
    matches = [
        task
        for task in parse_work_tasks(vault)
        if not task.completed
        and (task_date is None or task.task_date == task_date)
        and (
            (task.managed and normalized in task.title.casefold())
            or task.title.casefold() == normalized
        )
    ]
    if not matches:
        raise CommandCenterError(f"No open work task matches: {query}")
    if len(matches) > 1:
        raise CommandCenterError(
            f"Multiple open work tasks match: {query}",
            [asdict(task) for task in matches],
        )
    task = matches[0]
    note = vault / task.path
    with path_lock(note):
        lines = note.read_text(encoding="utf-8").splitlines()
        index = task.line_number - 1
        match = WORK_TASK_PATTERN.match(lines[index])
        if not match or match.group("state").lower() == "x":
            raise CommandCenterError("Work note changed while selecting the task.")
        if task.calendar_name and task.calendar_uid:
            update_synced_todo(
                task.sync_provider or "calendar",
                task.calendar_name,
                task.calendar_uid,
                title=task.title,
                completed=True,
            )
        lines[index] = (
            f"{match.group('prefix')}[x] {task.title}"
            f"{calendar_metadata(task.calendar_name, task.calendar_uid, task.sync_provider)}"
        )
        atomic_write(note, "\n".join(lines).rstrip() + "\n")
    audit_event(
        "completed",
        "work-task",
        task.title,
        {"date": task.task_date},
    )
    reconcile_next_day(vault, task.task_date)
    return asdict(task) | {"completed": True}


def reopen_work_task(
    vault: Path,
    query: str,
    task_date: str,
) -> dict[str, Any]:
    validate_iso_date(task_date)
    normalized = query.casefold().strip()
    matches = [
        task
        for task in parse_work_tasks(vault)
        if task.completed
        and task.task_date == task_date
        and task.title.casefold() == normalized
    ]
    if len(matches) != 1:
        raise CommandCenterError(
            f"Expected one completed Work task matching: {query}",
            [asdict(task) for task in matches],
        )
    task = matches[0]
    note = vault / task.path
    with path_lock(note):
        lines = note.read_text(encoding="utf-8").splitlines()
        index = task.line_number - 1
        match = WORK_TASK_PATTERN.match(lines[index])
        if not match or match.group("state").lower() != "x":
            raise CommandCenterError("Work note changed while selecting the task.")
        if task.calendar_name and task.calendar_uid:
            update_synced_todo(
                task.sync_provider or "calendar",
                task.calendar_name,
                task.calendar_uid,
                title=task.title,
                action_date=task_date,
                completed=False,
            )
        lines[index] = (
            f"{match.group('prefix')}[ ] {task.title}"
            f"{calendar_metadata(task.calendar_name, task.calendar_uid, task.sync_provider)}"
        )
        atomic_write(note, "\n".join(lines).rstrip() + "\n")
    audit_event(
        "reopened",
        "work-task",
        task.title,
        {"date": task_date},
    )
    reconcile_next_day(vault, task_date)
    return asdict(task) | {"completed": False}


def delete_work_task(
    vault: Path,
    query: str,
    task_date: str,
) -> dict[str, Any]:
    validate_iso_date(task_date)
    normalized = query.casefold().strip()
    immediate_children = [
        item
        for item in list_daily_tasks(vault, task_date, True)["work"]
        if item.get("parent_path")
        and item["parent_path"][-1].casefold() == normalized
    ]
    for child in immediate_children:
        delete_work_task(vault, child["title"], task_date)
    matches = [
        task
        for task in parse_work_tasks(vault)
        if task.task_date == task_date
        and task.title.casefold() == normalized
        and not task.title.endswith("→ διαγράφηκε")
    ]
    if len(matches) != 1:
        raise CommandCenterError(
            f"Expected one Work task matching: {query}",
            [asdict(task) for task in matches],
        )
    task = matches[0]
    if task.calendar_uid:
        delete_calendar_event_by_ref(
            task.calendar_name or "Work",
            task.calendar_uid,
        )
    note = vault / task.path
    with path_lock(note):
        lines = note.read_text(encoding="utf-8").splitlines()
        index = task.line_number - 1
        match = WORK_TASK_PATTERN.match(lines[index])
        if not match:
            raise CommandCenterError("Work note changed while deleting task.")
        lines[index] = (
            f"{match.group('prefix')}[x] {task.title} → διαγράφηκε"
        )
        atomic_write(note, "\n".join(lines).rstrip() + "\n")
    audit_event(
        "deleted",
        "work-task",
        task.title,
        {"date": task_date},
    )
    reconcile_next_day(vault, task_date)
    return {
        "title": task.title,
        "status": "deleted",
        "date": task_date,
    }


def reschedule_work_task(
    vault: Path,
    query: str,
    task_date: str,
) -> dict[str, Any]:
    validate_iso_date(task_date)
    normalized = query.casefold().strip()
    matches = [
        task
        for task in parse_work_tasks(vault)
        if task.managed
        and not task.completed
        and normalized in task.title.casefold()
    ]
    if not matches:
        raise CommandCenterError(f"No open Work task matches: {query}")
    if len(matches) > 1:
        raise CommandCenterError(
            f"Multiple open Work tasks match: {query}",
            [asdict(task) for task in matches],
        )
    task = matches[0]
    calendar_name = task.calendar_name or "Work"
    sync_provider = task.sync_provider or "calendar"
    calendar_uid = task.calendar_uid
    if calendar_uid:
        update_synced_todo(
            sync_provider,
            calendar_name,
            calendar_uid,
            title=task.title,
            action_date=task_date,
            completed=False,
        )
    else:
        calendar_uid = add_synced_todo(
            sync_provider,
            calendar_name,
            task.title,
            task_date,
        )

    source_note = vault / task.path
    target_note = work_daily_path(vault, date.fromisoformat(task_date))
    if source_note == target_note:
        with path_lock(source_note):
            lines = source_note.read_text(encoding="utf-8").splitlines()
            lines[task.line_number - 1] = (
                f"- [ ] {task.title}"
                f"{calendar_metadata(calendar_name, calendar_uid, sync_provider)}"
            )
            atomic_write(source_note, "\n".join(lines).rstrip() + "\n")
    else:
        with path_lock(source_note):
            lines = source_note.read_text(encoding="utf-8").splitlines()
            lines[task.line_number - 1] = (
                f"- [x] {task.title} → μεταφέρθηκε {task_date}"
                f"{calendar_metadata(calendar_name, calendar_uid, sync_provider)}"
            )
            atomic_write(source_note, "\n".join(lines).rstrip() + "\n")
        with path_lock(target_note):
            target_note.parent.mkdir(parents=True, exist_ok=True)
            content = (
                target_note.read_text(encoding="utf-8").rstrip()
                if target_note.exists()
                else ""
            )
            line = (
                f"- [ ] {task.title}"
                f"{calendar_metadata(calendar_name, calendar_uid, sync_provider)}"
            )
            atomic_write(
                target_note,
                append_line_to_section(content, "Command Center", line),
            )
    audit_event(
        "rescheduled",
        "work-task",
        task.title,
        {"from_date": task.task_date, "to_date": task_date},
    )
    reconcile_next_day(vault, task.task_date)
    reconcile_next_day(vault, task_date)
    return {
        "title": task.title,
        "from": task.task_date,
        "to": task_date,
        "calendar": calendar_name,
        "calendar_uid": calendar_uid,
        "sync_provider": sync_provider,
    }


def update_work_task(
    vault: Path,
    query: str,
    current_date: str,
    new_title: str,
    new_date: str,
) -> dict[str, Any]:
    validate_iso_date(current_date)
    validate_iso_date(new_date)
    normalized = query.casefold().strip()
    new_title = " ".join(new_title.split())
    if not new_title or "\n" in new_title or "\r" in new_title:
        raise CommandCenterError("Work task title must fit on one non-empty line.")
    matches = [
        task
        for task in parse_work_tasks(vault)
        if not task.completed
        and task.task_date == current_date
        and task.title.casefold() == normalized
    ]
    if len(matches) != 1:
        raise CommandCenterError(
            f"Expected one open Work task matching: {query}",
            [asdict(task) for task in matches],
        )
    task = matches[0]
    calendar_name = task.calendar_name or "Work"
    sync_provider = task.sync_provider or "calendar"
    calendar_uid = task.calendar_uid
    if calendar_uid:
        update_synced_todo(
            sync_provider,
            calendar_name,
            calendar_uid,
            title=new_title,
            action_date=new_date,
            completed=False,
        )
    else:
        calendar_uid = add_synced_todo(
            sync_provider,
            calendar_name,
            new_title,
            new_date,
        )
    source_note = vault / task.path
    target_note = work_daily_path(vault, date.fromisoformat(new_date))
    with path_lock(source_note):
        lines = source_note.read_text(encoding="utf-8").splitlines()
        index = task.line_number - 1
        match = WORK_TASK_PATTERN.match(lines[index])
        if not match or match.group("state").lower() == "x":
            raise CommandCenterError("Work note changed while selecting the task.")
        if source_note == target_note:
            lines[index] = (
                f"{match.group('prefix')}[ ] {new_title}"
                f"{calendar_metadata(calendar_name, calendar_uid, sync_provider)}"
            )
        else:
            lines[index] = (
                f"{match.group('prefix')}[x] {task.title} → μεταφέρθηκε {new_date}"
                f"{calendar_metadata(calendar_name, calendar_uid, sync_provider)}"
            )
        atomic_write(source_note, "\n".join(lines).rstrip() + "\n")
    if source_note != target_note:
        with path_lock(target_note):
            target_note.parent.mkdir(parents=True, exist_ok=True)
            content = (
                target_note.read_text(encoding="utf-8").rstrip()
                if target_note.exists()
                else ""
            )
            line = (
                f"- [ ] {new_title}"
                f"{calendar_metadata(calendar_name, calendar_uid, sync_provider)}"
            )
            atomic_write(
                target_note,
                append_line_to_section(content, "Command Center", line),
            )
    audit_event(
        "updated",
        "work-task",
        new_title,
        {
            "old_title": task.title,
            "from_date": current_date,
            "to_date": new_date,
        },
    )
    reconcile_next_day(vault, current_date)
    if new_date != current_date:
        reconcile_next_day(vault, new_date)
    return {
        "title": new_title,
        "old_title": task.title,
        "from_date": current_date,
        "to_date": new_date,
        "calendar": calendar_name,
        "calendar_uid": calendar_uid,
    }


def latest_markdown(directory: Path) -> Path | None:
    files = list(directory.glob("*.md")) if directory.is_dir() else []
    return max(files, key=lambda path: path.stat().st_mtime) if files else None


def work_sources(vault: Path) -> dict[str, Any]:
    work = vault / WORK_RELATIVE_PATH
    mappings = {
        "brag": work / "Brag doc",
        "one_on_one": work / "1-1",
        "connects": work / "Connects",
        "drawings": work / "Drawings",
    }
    return {
        key: [
            str(path.relative_to(vault))
            for path in sorted(directory.glob("*.md"))
        ]
        for key, directory in mappings.items()
    } | {
        "quarterly": "Work/Quarterly Tasks.md",
        "queries": "Work/Queries.md",
        "generic": "Work/Generic Notes.md",
        "updates": [
            str(path.relative_to(vault))
            for path in sorted(work.glob("Updates EngMs*.md"))
        ],
    }


def safe_work_note(vault: Path, relative_path: str) -> Path:
    work_root = (vault / WORK_RELATIVE_PATH).resolve()
    candidate = (vault / relative_path).resolve()
    if candidate != work_root and work_root not in candidate.parents:
        raise CommandCenterError("Work note must be inside the Work folder.")
    if candidate.suffix.lower() != ".md" or not candidate.is_file():
        raise CommandCenterError(f"Work note does not exist: {relative_path}")
    if "Drawings" in candidate.relative_to(work_root).parts:
        raise CommandCenterError("Work Drawings are index-only.")
    return candidate


def read_work_note(vault: Path, relative_path: str) -> dict[str, Any]:
    note = safe_work_note(vault, relative_path)
    return {
        "path": str(note.relative_to(vault)),
        "content": note.read_text(encoding="utf-8"),
    }


def search_work(vault: Path, query: str, limit: int) -> list[dict[str, Any]]:
    normalized = query.casefold().strip()
    if not normalized:
        raise CommandCenterError("Work search query cannot be empty.")
    results: list[dict[str, Any]] = []
    work_root = (vault / WORK_RELATIVE_PATH).resolve()
    for note in sorted(work_root.rglob("*.md")):
        resolved = note.resolve()
        if work_root not in resolved.parents:
            continue
        relative_parts = resolved.relative_to(work_root).parts
        if "1-1" in relative_parts or "Drawings" in relative_parts:
            continue
        for line_number, line in enumerate(
            resolved.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if normalized in line.casefold():
                results.append(
                    {
                        "path": str(note.relative_to(vault)),
                        "line_number": line_number,
                        "text": line.strip(),
                    }
                )
                if len(results) >= limit:
                    return results
    return results


def search_all(vault: Path, query: str, limit: int) -> list[dict[str, Any]]:
    normalized = " ".join(query.split()).casefold()
    if len(normalized) < 2:
        raise CommandCenterError("Search query must contain at least 2 characters.")
    if limit < 1 or limit > 100:
        raise CommandCenterError("Search limit must be between 1 and 100.")
    results: list[dict[str, Any]] = []

    def add(result: dict[str, Any]) -> None:
        if len(results) < limit:
            results.append(result)

    for task in parse_tasks(vault / TASKS_RELATIVE_PATH):
        if normalized in task.title.casefold():
            add(
                {
                    "kind": "task",
                    "title": task.title,
                    "context": task.section,
                    "path": str(TASKS_RELATIVE_PATH),
                    "completed": task.completed,
                }
            )
    for project in load_projects(vault):
        summary = project_summary(vault / project.note_path)
        if normalized in project.name.casefold() or normalized in summary.casefold():
            add(
                {
                    "kind": "project",
                    "title": project.name,
                    "context": summary,
                    "path": project.note_path,
                }
            )
        for record in project_records(vault / project.note_path):
            if record.active and normalized in record.text.casefold():
                add(
                    {
                        "kind": "project-record",
                        "title": record.text,
                        "context": project.name,
                        "path": project.note_path,
                    }
                )
    for item in parse_learning(vault):
        if normalized in item.title.casefold():
            add(
                {
                    "kind": "learning",
                    "title": item.title,
                    "context": item.kind,
                    "path": str(LEARNING_RELATIVE_PATH),
                    "url": item.url,
                    "completed": item.completed,
                }
            )
    for item in inbox_items(vault):
        if normalized in item["text"].casefold():
            add(
                {
                    "kind": "inbox",
                    "title": item["text"],
                    "context": item.get("project"),
                    "path": str(INBOX_RELATIVE_PATH),
                }
            )
    if len(results) < limit:
        for match in search_work(vault, query, limit - len(results)):
            add(
                {
                    "kind": "work",
                    "title": match["text"],
                    "context": match["path"],
                    "path": match["path"],
                    "line_number": match["line_number"],
                }
            )
    return results


def work_target(
    vault: Path,
    kind: str,
    target_date: str | None,
) -> Path:
    work = vault / WORK_RELATIVE_PATH
    if kind == "one_on_one":
        if not target_date:
            raise CommandCenterError("--date is required for a 1-1 note.")
        validate_iso_date(target_date)
        return work / "1-1" / f"{target_date}.md"
    fixed = {
        "quarterly": work / "Quarterly Tasks.md",
        "queries": work / "Queries.md",
        "generic": work / "Generic Notes.md",
    }
    if kind in fixed:
        return fixed[kind]
    directories = {
        "brag": work / "Brag doc",
        "connects": work / "Connects",
    }
    latest = latest_markdown(directories[kind])
    if latest is None:
        filename = (
            f"{date.today().isoformat()}.md"
            if kind == "brag"
            else f"{date.today().strftime('%Y-%m')}.md"
        )
        return directories[kind] / filename
    return latest


def append_work_note(
    vault: Path,
    kind: str,
    text: str,
    target_date: str | None,
) -> dict[str, Any]:
    normalized = " ".join(text.split())
    if not normalized or "\n" in text or "\r" in text:
        raise CommandCenterError("Work entry must fit on one non-empty line.")
    note = work_target(vault, kind, target_date)
    with path_lock(note):
        note.parent.mkdir(parents=True, exist_ok=True)
        content = note.read_text(encoding="utf-8").rstrip() if note.exists() else ""
        atomic_write(
            note,
            append_line_to_section(content, "Command Center", f"- {normalized}"),
        )
    return {
        "kind": kind,
        "text": normalized,
        "path": str(note.relative_to(vault)),
    }


def work_briefing(vault: Path) -> dict[str, Any]:
    today = date.today()
    open_tasks = [task for task in parse_work_tasks(vault) if not task.completed]
    today_tasks = [task for task in open_tasks if task.task_date == today.isoformat()]
    recent_overdue = [
        task
        for task in open_tasks
        if today - timedelta(days=30)
        <= date.fromisoformat(task.task_date)
        < today
    ]
    older_open_count = sum(
        date.fromisoformat(task.task_date) < today - timedelta(days=30)
        for task in open_tasks
    )
    sources = work_sources(vault)
    return {
        "today": [asdict(task) for task in today_tasks],
        "next": next_work_task(vault),
        "recent_overdue": [asdict(task) for task in recent_overdue],
        "older_open_count": older_open_count,
        "latest_one_on_one": sources["one_on_one"][-1]
        if sources["one_on_one"]
        else None,
        "latest_brag": sources["brag"][-1] if sources["brag"] else None,
        "latest_connects": sources["connects"][-1]
        if sources["connects"]
        else None,
    }


def credential(name: str, keychain_service: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    result = run_process(
        ["security", "find-generic-password", "-s", keychain_service, "-w"],
        allow_failure=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    raise IntegrationError(
        f"{name} is not configured. Store it in macOS Keychain service "
        f"'{keychain_service}'."
    )


def personal_health() -> dict[str, Any]:
    base_url = credential(
        "COMMAND_CENTER_SUPABASE_URL",
        "command-center-supabase-url",
    ).rstrip("/")
    service_key = credential(
        "COMMAND_CENTER_SUPABASE_SERVICE_KEY",
        "command-center-supabase-service",
    )
    user_id = credential(
        "COMMAND_CENTER_SUPABASE_USER_ID",
        "command-center-supabase-user",
    )
    if not re.fullmatch(
        r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}",
        user_id,
    ):
        raise IntegrationError("Supabase user ID is invalid.")
    query = urllib.parse.urlencode(
        {
            "user_id": f"eq.{user_id}",
            "select": (
                "day,steps,sleep_minutes,active_energy_kcal,"
                "resting_heart_rate,updated_at"
            ),
            "order": "day.desc",
            "limit": "7",
        }
    )
    request = urllib.request.Request(
        f"{base_url}/rest/v1/command_center_health_daily?{query}",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            rows = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise IntegrationError(
            f"Supabase Health returned HTTP {exc.code}."
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise IntegrationError(
            f"Supabase Health request failed: {type(exc).__name__}."
        ) from exc
    return {"rows": rows}


def scratchpad_get() -> dict[str, Any]:
    base_url = credential(
        "COMMAND_CENTER_SUPABASE_URL",
        "command-center-supabase-url",
    ).rstrip("/")
    service_key = credential(
        "COMMAND_CENTER_SUPABASE_SERVICE_KEY",
        "command-center-supabase-service",
    )
    user_id = credential(
        "COMMAND_CENTER_SUPABASE_USER_ID",
        "command-center-supabase-user",
    )
    request = urllib.request.Request(
        f"{base_url}/rest/v1/command_center_scratchpad"
        f"?user_id=eq.{urllib.parse.quote(user_id)}"
        "&select=content,updated_at",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            rows = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise IntegrationError(
            f"Supabase Scratchpad returned HTTP {exc.code}."
        ) from exc
    return rows[0] if rows else {"content": "", "updated_at": None}


def scratchpad_set(content: str) -> dict[str, Any]:
    if len(content) > 20_000:
        raise CommandCenterError("Scratchpad content exceeds 20,000 characters.")
    base_url = credential(
        "COMMAND_CENTER_SUPABASE_URL",
        "command-center-supabase-url",
    ).rstrip("/")
    service_key = credential(
        "COMMAND_CENTER_SUPABASE_SERVICE_KEY",
        "command-center-supabase-service",
    )
    user_id = credential(
        "COMMAND_CENTER_SUPABASE_USER_ID",
        "command-center-supabase-user",
    )
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    request = urllib.request.Request(
        f"{base_url}/rest/v1/command_center_scratchpad?on_conflict=user_id",
        data=json.dumps(
            {"user_id": user_id, "content": content, "updated_at": now}
        ).encode("utf-8"),
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20):
            pass
    except urllib.error.HTTPError as exc:
        raise IntegrationError(
            f"Supabase Scratchpad returned HTTP {exc.code}."
        ) from exc
    return {"content": content, "updated_at": now}


def scratchpad_clear() -> dict[str, Any]:
    base_url = credential(
        "COMMAND_CENTER_SUPABASE_URL",
        "command-center-supabase-url",
    ).rstrip("/")
    service_key = credential(
        "COMMAND_CENTER_SUPABASE_SERVICE_KEY",
        "command-center-supabase-service",
    )
    user_id = credential(
        "COMMAND_CENTER_SUPABASE_USER_ID",
        "command-center-supabase-user",
    )
    request = urllib.request.Request(
        f"{base_url}/rest/v1/command_center_scratchpad"
        f"?user_id=eq.{urllib.parse.quote(user_id)}",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
        },
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(request, timeout=20):
            pass
    except urllib.error.HTTPError as exc:
        raise IntegrationError(
            f"Supabase Scratchpad returned HTTP {exc.code}."
        ) from exc
    return {"content": "", "updated_at": None}


def cloud_sync_status() -> dict[str, Any]:
    base_url = credential(
        "COMMAND_CENTER_SUPABASE_URL",
        "command-center-supabase-url",
    ).rstrip("/")
    service_key = credential(
        "COMMAND_CENTER_SUPABASE_SERVICE_KEY",
        "command-center-supabase-service",
    )
    user_id = credential(
        "COMMAND_CENTER_SUPABASE_USER_ID",
        "command-center-supabase-user",
    )
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Accept": "application/json",
    }

    def read(path: str) -> Any:
        request = urllib.request.Request(
            f"{base_url}/rest/v1/{path}",
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise IntegrationError(
                f"Supabase sync status returned HTTP {exc.code}."
            ) from exc

    snapshot_rows = read(
        "command_center_snapshots"
        f"?user_id=eq.{urllib.parse.quote(user_id)}"
        "&select=updated_at,version"
    )
    command_rows = read(
        "command_center_commands"
        f"?user_id=eq.{urllib.parse.quote(user_id)}"
        "&status=in.(pending,processing,failed)"
        "&select=id,action,status,created_at,processed_at,result"
        "&order=created_at.desc&limit=50"
    )
    counts = {
        status: sum(row["status"] == status for row in command_rows)
        for status in ("pending", "processing", "failed")
    }
    return {
        "last_snapshot_at": (
            snapshot_rows[0]["updated_at"] if snapshot_rows else None
        ),
        "version": snapshot_rows[0]["version"] if snapshot_rows else None,
        "counts": counts,
        "failures": [
            row for row in command_rows if row["status"] == "failed"
        ][:10],
    }


def daily_snapshot_list() -> list[dict[str, Any]]:
    base_url = credential(
        "COMMAND_CENTER_SUPABASE_URL",
        "command-center-supabase-url",
    ).rstrip("/")
    service_key = credential(
        "COMMAND_CENTER_SUPABASE_SERVICE_KEY",
        "command-center-supabase-service",
    )
    user_id = credential(
        "COMMAND_CENTER_SUPABASE_USER_ID",
        "command-center-supabase-user",
    )
    request = urllib.request.Request(
        f"{base_url}/rest/v1/command_center_daily_snapshots"
        f"?user_id=eq.{urllib.parse.quote(user_id)}"
        "&select=day,updated_at&order=day.desc&limit=365",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def daily_snapshot_get(snapshot_date: str) -> dict[str, Any]:
    validate_iso_date(snapshot_date)
    base_url = credential(
        "COMMAND_CENTER_SUPABASE_URL",
        "command-center-supabase-url",
    ).rstrip("/")
    service_key = credential(
        "COMMAND_CENTER_SUPABASE_SERVICE_KEY",
        "command-center-supabase-service",
    )
    user_id = credential(
        "COMMAND_CENTER_SUPABASE_USER_ID",
        "command-center-supabase-user",
    )
    request = urllib.request.Request(
        f"{base_url}/rest/v1/command_center_daily_snapshots"
        f"?user_id=eq.{urllib.parse.quote(user_id)}"
        f"&day=eq.{urllib.parse.quote(snapshot_date)}"
        "&select=day,payload,updated_at",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        rows = json.loads(response.read().decode("utf-8"))
    if not rows:
        raise CommandCenterError(f"No daily snapshot exists for {snapshot_date}.")
    return rows[0]


def http_json(url: str, token: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "CommandCenter/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise IntegrationError(f"BookIt API returned HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise IntegrationError(f"BookIt API request failed: {type(exc).__name__}.") from exc


def bookit_business() -> dict[str, Any]:
    token = credential("BOOKIT_ADMIN_TOKEN", "command-center-bookit-admin")
    base_url = os.environ.get(
        "BOOKIT_API_URL",
        "https://api.bookit.fyi",
    ).rstrip("/")
    overview = http_json(f"{base_url}/admin/metrics/overview", token)
    subscriptions = http_json(f"{base_url}/admin/subscriptions", token)
    now = datetime.now().astimezone()
    renewal_cutoff = now + timedelta(days=30)
    rows = subscriptions.get("rows", [])
    active = [
        row
        for row in rows
        if row.get("billing_managed")
        and row.get("status") == "active"
        and not row.get("cancelling")
    ]
    trials = [
        row
        for row in rows
        if row.get("billing_managed") and row.get("status") == "trialing"
    ]
    cancelling = [row for row in rows if row.get("cancelling")]
    attention_statuses = {
        "past_due",
        "unpaid",
        "incomplete",
        "incomplete_expired",
    }
    attention = [
        row
        for row in rows
        if row.get("sync_error") or row.get("status") in attention_statuses
    ]
    manual = [row for row in rows if not row.get("billing_managed")]
    renewing_soon = [
        row
        for row in active
        if (renewal := parse_optional_datetime(row.get("next_billing_at")))
        and now <= renewal <= renewal_cutoff
    ]
    for collection in (active, trials, cancelling, attention, manual, renewing_soon):
        collection.sort(
            key=lambda row: (
                row.get("next_billing_at")
                or row.get("ends_at")
                or "9999",
                str(row.get("display_name") or "").casefold(),
            )
        )
    return {
        "overview": overview,
        "metrics": {
            key: subscriptions.get(key)
            for key in (
                "total_paid_plans",
                "active",
                "trialing",
                "cancelling",
                "attention",
                "mrr_cents",
                "trial_mrr_cents",
                "cancelling_mrr_cents",
                "currency",
            )
        },
        "active": active,
        "trials": trials,
        "renewing_soon": renewing_soon,
        "cancelling": cancelling,
        "attention": attention,
        "manual": manual,
    }


def parse_optional_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone()


def render_logs(
    vault: Path,
    name: str,
    limit: int,
    level: str | None,
    text: str | None,
) -> dict[str, Any]:
    project = project_by_name(vault, name)
    if not project.render_service_ids:
        raise CommandCenterError(f"No Render service is registered for {name}.")
    validate_project_metadata(
        project.render_service_ids,
        project.resend_domains,
        project.source_paths,
        [],
    )
    if limit < 1 or limit > 100:
        raise CommandCenterError("Render log limit must be between 1 and 100.")
    command = [
        "render",
        "logs",
        "--resources",
        ",".join(project.render_service_ids),
        "--limit",
        str(limit),
        "--output",
        "json",
    ]
    if level:
        command.extend(["--level", level])
    if text:
        command.extend(["--text", text])
    result = run_process(command)
    entries = parse_json_stream(result.stdout)
    logs = []
    for entry in entries:
        labels = {
            label.get("name"): label.get("value")
            for label in entry.get("labels", [])
            if isinstance(label, dict)
        }
        logs.append(
            {
                "timestamp": entry.get("timestamp"),
                "level": labels.get("level"),
                "type": labels.get("type"),
                "message": redact_external_text(str(entry.get("message") or "")),
            }
        )
    return {"project": project.name, "logs": logs}


def resend_activity(vault: Path, name: str, limit: int) -> dict[str, Any]:
    project = project_by_name(vault, name)
    if not project.resend_domains:
        raise CommandCenterError(f"No Resend domain is registered for {name}.")
    if limit < 1 or limit > 100:
        raise CommandCenterError("Resend limit must be between 1 and 100.")
    validate_project_metadata(
        project.render_service_ids,
        project.resend_domains,
        project.source_paths,
        [],
    )
    token = credential("RESEND_API_KEY", "command-center-resend-api")
    domains = tuple(f"@{domain.casefold()}" for domain in project.resend_domains)
    rows = []
    counts: dict[str, int] = {}
    cursor: str | None = None
    pages_scanned = 0
    has_more = True
    while has_more and len(rows) < limit and pages_scanned < 20:
        query = {"limit": "100"}
        if cursor:
            query["after"] = cursor
        response = http_json(
            f"https://api.resend.com/emails?{urllib.parse.urlencode(query)}",
            token,
        )
        pages_scanned += 1
        data = response.get("data", [])
        for email in data:
            sender = str(email.get("from") or "")
            if not sender.casefold().endswith(domains) and not any(
                domain in sender.casefold() for domain in domains
            ):
                continue
            event = str(email.get("last_event") or "unknown")
            counts[event] = counts.get(event, 0) + 1
            rows.append(
                {
                    "created_at": email.get("created_at"),
                    "subject": redact_external_text(
                        str(email.get("subject") or "")
                    ),
                    "recipients": [
                        mask_email(str(recipient))
                        for recipient in email.get("to") or []
                    ],
                    "last_event": event,
                }
            )
            if len(rows) >= limit:
                break
        has_more = bool(response.get("has_more"))
        cursor = str(data[-1].get("id")) if data else None
        if has_more and not cursor:
            break
    return {
        "project": project.name,
        "summary": counts,
        "emails": rows,
        "recipients_masked": True,
        "pages_scanned": pages_scanned,
        "truncated": has_more and pages_scanned >= 20,
    }


def weekly_review(vault: Path) -> dict[str, Any]:
    health = project_health(vault)
    learning = list_learning(vault, None, None, False)
    records = {
        project.name: len(
            [record for record in project_records(vault / project.note_path) if record.active]
        )
        for project in load_projects(vault)
        if project.status == "active"
    }
    return {
        "tasks": [
            task
            for task in list_tasks(vault, "all", None)
            if task["relation"] != "future"
        ],
        "inbox_count": len(inbox_items(vault)),
        "learning_pending": len(learning),
        "work": work_briefing(vault),
        "project_records": records,
        "health": health,
    }


def dashboard(vault: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "tasks": list_tasks(vault, "action", None),
        "work": None,
        "health": None,
        "github": None,
        "calendar": None,
        "mail": None,
        "errors": {},
    }
    integrations = {
        "work": lambda: work_briefing(vault),
        "health": lambda: project_health(vault),
        "github": github_attention,
        "calendar": calendar_today,
        "mail": lambda: mail_attention(None),
    }
    for name, operation in integrations.items():
        try:
            payload[name] = operation()
        except IntegrationError as exc:
            payload["errors"][name] = str(exc)
    return payload


def home(
    vault: Path,
    include_personal: bool,
    include_work: bool,
    include_weekly: bool = True,
) -> dict[str, Any]:
    daily_tasks: dict[str, Any] = {}
    rollover_date = date.today().isoformat()
    generated_daily_tasks = list_daily_tasks(vault, rollover_date)
    if include_personal:
        daily_tasks["personal"] = generated_daily_tasks["personal"]
    if include_work:
        daily_tasks["work"] = generated_daily_tasks["work"]
    payload = {
        "morning": dashboard(vault),
        "daily_tasks": daily_tasks,
        "daily_tasks_included": {
            "personal": include_personal,
            "work": include_work,
        },
    }
    if include_weekly:
        payload["weekly"] = weekly_review(vault)
    return payload


def exception_center(vault: Path) -> dict[str, Any]:
    exceptions: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    overdue_tasks = list_tasks(vault, "overdue", None)
    exceptions.extend(
        {"kind": "task", "severity": "warning", "item": task}
        for task in overdue_tasks
    )
    waiting = list_waiting_on(vault, False)
    exceptions.extend(
        {"kind": "waiting-on", "severity": "warning", "item": item}
        for item in waiting
        if item["overdue"]
    )

    try:
        health = project_health(vault)
        exceptions.extend(
            {"kind": "health", "severity": "critical", "item": check}
            for check in health
            if not check["up"]
        )
    except IntegrationError as exc:
        errors["health"] = str(exc)

    try:
        github = github_attention()
        exceptions.extend(
            {"kind": "ci", "severity": "critical", "item": failure}
            for failure in github["failing_ci"]
        )
    except IntegrationError as exc:
        errors["github"] = str(exc)

    projects = load_projects(vault)
    bookit = next(
        (project for project in projects if project.name.casefold() == "bookit"),
        None,
    )
    if bookit:
        try:
            business = bookit_business()
            for row in business["attention"]:
                exceptions.append(
                    {
                        "kind": "subscription",
                        "severity": "critical",
                        "item": {
                            "display_name": row.get("display_name"),
                            "status": row.get("status"),
                            "sync_error": row.get("sync_error"),
                        },
                    }
                )
            for row in business["trials"]:
                exceptions.append(
                    {
                        "kind": "trial",
                        "severity": "warning",
                        "item": {
                            "display_name": row.get("display_name"),
                            "ends_at": row.get("ends_at"),
                        },
                    }
                )
            for row in business["cancelling"]:
                exceptions.append(
                    {
                        "kind": "cancellation",
                        "severity": "warning",
                        "item": {
                            "display_name": row.get("display_name"),
                            "ends_at": row.get("ends_at"),
                        },
                    }
                )
            for row in business["renewing_soon"]:
                exceptions.append(
                    {
                        "kind": "renewal",
                        "severity": "info",
                        "item": {
                            "display_name": row.get("display_name"),
                            "next_billing_at": row.get("next_billing_at"),
                        },
                    }
                )
        except IntegrationError as exc:
            errors["bookit"] = str(exc)

    for project in projects:
        if not project.resend_domains:
            continue
        try:
            resend = resend_activity(vault, project.name, 5)
            for email in resend["emails"]:
                if str(email["last_event"]).lower() in {"bounced", "failed"}:
                    exceptions.append(
                        {
                            "kind": "email",
                            "severity": "critical",
                            "item": {
                                "project": project.name,
                                "subject": email["subject"],
                                "recipients": email["recipients"],
                                "last_event": email["last_event"],
                            },
                        }
                    )
        except IntegrationError as exc:
            errors[f"resend:{project.name}"] = str(exc)

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    exceptions.sort(key=lambda entry: severity_order[entry["severity"]])
    return {
        "exceptions": exceptions,
        "waiting_on": waiting,
        "summary": {
            "total": len(exceptions),
            "critical": sum(item["severity"] == "critical" for item in exceptions),
            "warning": sum(item["severity"] == "warning" for item in exceptions),
            "info": sum(item["severity"] == "info" for item in exceptions),
        },
        "errors": errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(description="Obsidian command-center helper")
    parser.add_argument("--vault", help="Override the Obsidian vault path")
    commands = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=JsonArgumentParser,
    )

    task_list = commands.add_parser("task-list")
    task_list.add_argument(
        "--view",
        choices=["action", "today", "overdue", "inbox", "week", "all"],
        default="action",
    )
    task_list.add_argument("--project")

    task_add = commands.add_parser("task-add")
    task_add.add_argument("--title", required=True)
    task_add.add_argument("--area", choices=["Personal", "Work"])
    task_add.add_argument("--project")
    task_add.add_argument("--date")
    task_add.add_argument("--parent-line", type=int)

    task_complete = commands.add_parser("task-complete")
    task_complete.add_argument("--query", required=True)
    task_complete.add_argument("--date")
    task_reopen = commands.add_parser("task-reopen")
    task_reopen.add_argument("--query", required=True)
    task_reopen.add_argument("--date", required=True)
    task_delete = commands.add_parser("task-delete")
    task_delete.add_argument("--query", required=True)
    task_delete.add_argument("--date", required=True)

    task_reschedule = commands.add_parser("task-reschedule")
    task_reschedule.add_argument("--query", required=True)
    task_reschedule.add_argument("--date", required=True)
    task_update = commands.add_parser("task-update")
    task_update.add_argument("--query", required=True)
    task_update.add_argument("--current-date", required=True)
    task_update.add_argument("--title", required=True)
    task_update.add_argument("--date", required=True)

    commands.add_parser("project-list")
    project_status_parser = commands.add_parser("project-status")
    project_status_parser.add_argument("--name", required=True)
    project_records_parser = commands.add_parser("project-records")
    project_records_parser.add_argument("--name", required=True)
    project_records_parser.add_argument(
        "--kind",
        choices=["requirement", "fact", "idea", "decision", "note", "summary"],
    )
    project_record_parser = commands.add_parser("project-record")
    project_record_parser.add_argument("--name", required=True)
    project_record_parser.add_argument(
        "--kind",
        required=True,
        choices=["requirement", "fact", "idea", "decision", "note"],
    )
    project_record_parser.add_argument("--text", required=True)
    project_record_parser.add_argument("--source", required=True)
    project_record_parser.add_argument("--supersedes")
    project_archive_parser = commands.add_parser("project-record-archive")
    project_archive_parser.add_argument("--name", required=True)
    project_archive_parser.add_argument("--id", required=True)
    project_archive_parser.add_argument(
        "--source",
        default="Command Center",
    )
    summary_parser = commands.add_parser("project-summary-set")
    summary_parser.add_argument("--name", required=True)
    summary_parser.add_argument("--text", required=True)
    summary_parser.add_argument("--source", required=True)
    project_add = commands.add_parser("project-add")
    project_add.add_argument("--name")
    project_add.add_argument("--path")
    project_add.add_argument("--github")
    project_add.add_argument("--area", choices=["personal", "work"], default="personal")
    project_add.add_argument(
        "--lifecycle",
        choices=["planned", "development", "live", "maintenance", "paused"],
        default="development",
    )
    project_add.add_argument("--source-path", action="append", default=[])
    project_add.add_argument("--health-check", action="append", default=[])
    project_add.add_argument("--render-service-id", action="append", default=[])
    project_add.add_argument("--resend-domain", action="append", default=[])
    project_health_parser = commands.add_parser("project-health")
    project_health_parser.add_argument("--name")
    project_health_set = commands.add_parser("project-health-set")
    project_health_set.add_argument("--name", required=True)
    project_health_set.add_argument(
        "--health-check",
        action="append",
        required=True,
    )
    project_health_set.add_argument("--source", required=True)

    capture = commands.add_parser("capture")
    capture.add_argument("--text", required=True)
    capture.add_argument("--source", default="Χρήστης (chat)")
    capture.add_argument("--project")
    commands.add_parser("inbox-list")
    waiting_add = commands.add_parser("waiting-add")
    waiting_add.add_argument("--person", required=True)
    waiting_add.add_argument("--item", required=True)
    waiting_add.add_argument("--due")
    waiting_list = commands.add_parser("waiting-list")
    waiting_list.add_argument("--include-completed", action="store_true")
    waiting_complete = commands.add_parser("waiting-complete")
    waiting_complete.add_argument("--query", required=True)

    learning_list = commands.add_parser("learning-list")
    learning_list.add_argument("--kind", choices=list(LEARNING_KINDS))
    learning_list.add_argument("--project")
    learning_list.add_argument("--include-done", action="store_true")
    learning_add = commands.add_parser("learning-add")
    learning_add.add_argument("--title", required=True)
    learning_add.add_argument("--kind", required=True, choices=list(LEARNING_KINDS))
    learning_add.add_argument("--url")
    learning_add.add_argument("--project")
    learning_add.add_argument("--source", default="Χρήστης (chat)")
    learning_complete = commands.add_parser("learning-complete")
    learning_complete.add_argument("--query", required=True)

    commands.add_parser("work-briefing")
    commands.add_parser("work-sources")
    work_read = commands.add_parser("work-read")
    work_read.add_argument("--path", required=True)
    work_search = commands.add_parser("work-search")
    work_search.add_argument("--query", required=True)
    work_search.add_argument("--limit", type=int, default=50)
    search_parser = commands.add_parser("search")
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--limit", type=int, default=50)
    work_task_add = commands.add_parser("work-task-add")
    work_task_add.add_argument("--title", required=True)
    work_task_add.add_argument("--date", required=True)
    work_task_add.add_argument("--parent-line", type=int)
    work_task_complete = commands.add_parser("work-task-complete")
    work_task_complete.add_argument("--query", required=True)
    work_task_complete.add_argument("--date")
    work_task_reopen = commands.add_parser("work-task-reopen")
    work_task_reopen.add_argument("--query", required=True)
    work_task_reopen.add_argument("--date", required=True)
    work_task_delete = commands.add_parser("work-task-delete")
    work_task_delete.add_argument("--query", required=True)
    work_task_delete.add_argument("--date", required=True)
    work_task_reschedule = commands.add_parser("work-task-reschedule")
    work_task_reschedule.add_argument("--query", required=True)
    work_task_reschedule.add_argument("--date", required=True)
    work_task_update = commands.add_parser("work-task-update")
    work_task_update.add_argument("--query", required=True)
    work_task_update.add_argument("--current-date", required=True)
    work_task_update.add_argument("--title", required=True)
    work_task_update.add_argument("--date", required=True)
    work_append = commands.add_parser("work-append")
    work_append.add_argument(
        "--kind",
        required=True,
        choices=["brag", "connects", "one_on_one", "quarterly", "queries", "generic"],
    )
    work_append.add_argument("--text", required=True)
    work_append.add_argument("--date")

    commands.add_parser("github")
    commands.add_parser("calendar-list")
    commands.add_parser("calendar-today")
    calendar_upcoming_parser = commands.add_parser("calendar-upcoming")
    calendar_upcoming_parser.add_argument("--minutes", type=int, default=15)
    calendar_range_parser = commands.add_parser("calendar-range")
    calendar_range_parser.add_argument("--days", type=int, default=14)
    calendar_add = commands.add_parser("calendar-add")
    calendar_add.add_argument("--calendar", required=True)
    calendar_add.add_argument("--title", required=True)
    calendar_add.add_argument("--start", required=True)
    calendar_add.add_argument("--duration", type=int, default=60)
    agenda_delete = commands.add_parser("agenda-delete")
    agenda_delete.add_argument(
        "--kind",
        required=True,
        choices=["event", "reminder"],
    )
    agenda_delete.add_argument("--calendar", required=True)
    agenda_delete.add_argument("--uid", required=True)
    agenda_delete.add_argument("--title", required=True)
    agenda_delete.add_argument("--ref")
    reminder_list = commands.add_parser("reminder-list")
    reminder_list.add_argument("--list", default="Reminders")
    reminder_add = commands.add_parser("reminder-add")
    reminder_add.add_argument("--list", default="Reminders")
    reminder_add.add_argument("--title", required=True)
    reminder_add.add_argument("--date")
    reminder_complete = commands.add_parser("reminder-complete")
    reminder_complete.add_argument("--list", default="Reminders")
    reminder_complete.add_argument("--id", required=True)
    reminder_update = commands.add_parser("reminder-update")
    reminder_update.add_argument("--list", default="Reminders")
    reminder_update.add_argument("--id", required=True)
    reminder_update.add_argument("--title", required=True)
    reminder_update.add_argument("--date", required=True)

    mail = commands.add_parser("mail")
    mail.add_argument("--query")
    mail.add_argument("--unread-only", action="store_true")
    mail.add_argument("--account")
    commands.add_parser("bookit-business")
    commands.add_parser("health-personal")
    commands.add_parser("scratchpad-get")
    scratchpad_set_parser = commands.add_parser("scratchpad-set")
    scratchpad_set_parser.add_argument("--content", required=True)
    commands.add_parser("scratchpad-clear")
    audit_parser = commands.add_parser("audit-list")
    audit_parser.add_argument("--limit", type=int, default=100)
    commands.add_parser("sync-status")
    commands.add_parser("snapshot-list")
    snapshot_get = commands.add_parser("snapshot-get")
    snapshot_get.add_argument("--date", required=True)
    render_logs_parser = commands.add_parser("render-logs")
    render_logs_parser.add_argument("--name", required=True)
    render_logs_parser.add_argument("--limit", type=int, default=30)
    render_logs_parser.add_argument("--level")
    render_logs_parser.add_argument("--text")
    resend_parser = commands.add_parser("resend-emails")
    resend_parser.add_argument("--name", required=True)
    resend_parser.add_argument("--limit", type=int, default=5)
    commands.add_parser("weekly-review")
    commands.add_parser("dashboard")
    commands.add_parser("exceptions")
    daily_rollover_parser = commands.add_parser("daily-rollover")
    daily_rollover_parser.add_argument("--date", default=date.today().isoformat())
    daily_tasks_parser = commands.add_parser("daily-tasks")
    daily_tasks_parser.add_argument("--date", default=date.today().isoformat())
    daily_tasks_parser.add_argument("--include-completed", action="store_true")
    home_parser = commands.add_parser("home")
    home_parser.add_argument("--include-personal", action="store_true")
    home_parser.add_argument("--include-work", action="store_true")
    home_parser.add_argument("--morning-only", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        vault = discover_vault(args.vault)
        if args.command == "task-list":
            emit({"tasks": list_tasks(vault, args.view, args.project)})
        elif args.command == "task-add":
            emit(
                add_task(
                    vault,
                    args.title,
                    args.area,
                    args.project,
                    args.date,
                    args.parent_line,
                )
            )
        elif args.command == "task-complete":
            emit(complete_task(vault, args.query, args.date))
        elif args.command == "task-reopen":
            emit(reopen_task(vault, args.query, args.date))
        elif args.command == "task-delete":
            emit(delete_task(vault, args.query, args.date))
        elif args.command == "task-reschedule":
            emit(reschedule_task(vault, args.query, args.date))
        elif args.command == "task-update":
            emit(
                update_task(
                    vault,
                    args.query,
                    args.current_date,
                    args.title,
                    args.date,
                )
            )
        elif args.command == "project-list":
            emit({"projects": [asdict(project) for project in load_projects(vault)]})
        elif args.command == "project-status":
            emit(project_status(vault, args.name))
        elif args.command == "project-records":
            records = project_records(project_note(vault, args.name))
            if args.kind:
                records = [record for record in records if record.kind == args.kind]
            emit({"records": [asdict(record) for record in records]})
        elif args.command == "project-record-archive":
            emit(
                archive_project_record(
                    vault,
                    args.name,
                    args.id,
                    args.source,
                )
            )
        elif args.command == "project-record":
            emit(
                asdict(
                    record_project(
                        vault,
                        args.name,
                        args.kind,
                        args.text,
                        args.source,
                        args.supersedes,
                    )
                )
            )
        elif args.command == "project-summary-set":
            emit(
                set_project_summary(
                    vault,
                    args.name,
                    args.text,
                    args.source,
                )
            )
        elif args.command == "project-add":
            emit(
                asdict(
                    add_project(
                        vault,
                        args.name,
                        args.area,
                        args.lifecycle,
                        args.path,
                        args.github,
                        args.render_service_id,
                        args.resend_domain,
                        args.source_path,
                        args.health_check,
                    )
                )
            )
        elif args.command == "project-health":
            emit({"checks": project_health(vault, args.name)})
        elif args.command == "project-health-set":
            emit(
                set_project_health_checks(
                    vault,
                    args.name,
                    args.health_check,
                    args.source,
                )
            )
        elif args.command == "capture":
            emit(capture_note(vault, args.text, args.source, args.project))
        elif args.command == "inbox-list":
            emit({"items": inbox_items(vault)})
        elif args.command == "waiting-add":
            emit(add_waiting_on(vault, args.person, args.item, args.due))
        elif args.command == "waiting-list":
            emit(
                {
                    "items": list_waiting_on(
                        vault,
                        args.include_completed,
                    )
                }
            )
        elif args.command == "waiting-complete":
            emit(complete_waiting_on(vault, args.query))
        elif args.command == "learning-list":
            emit(
                {
                    "items": list_learning(
                        vault,
                        args.kind,
                        args.project,
                        args.include_done,
                    )
                }
            )
        elif args.command == "learning-add":
            emit(
                add_learning(
                    vault,
                    args.title,
                    args.kind,
                    args.url,
                    args.project,
                    args.source,
                )
            )
        elif args.command == "learning-complete":
            emit(complete_learning(vault, args.query))
        elif args.command == "work-briefing":
            emit(work_briefing(vault))
        elif args.command == "work-sources":
            emit(work_sources(vault))
        elif args.command == "work-read":
            emit(read_work_note(vault, args.path))
        elif args.command == "work-search":
            emit({"matches": search_work(vault, args.query, args.limit)})
        elif args.command == "search":
            emit({"results": search_all(vault, args.query, args.limit)})
        elif args.command == "work-task-add":
            emit(
                add_work_task(
                    vault,
                    args.title,
                    args.date,
                    args.parent_line,
                )
            )
        elif args.command == "work-task-complete":
            emit(complete_work_task(vault, args.query, args.date))
        elif args.command == "work-task-reopen":
            emit(reopen_work_task(vault, args.query, args.date))
        elif args.command == "work-task-delete":
            emit(delete_work_task(vault, args.query, args.date))
        elif args.command == "work-task-reschedule":
            emit(reschedule_work_task(vault, args.query, args.date))
        elif args.command == "work-task-update":
            emit(
                update_work_task(
                    vault,
                    args.query,
                    args.current_date,
                    args.title,
                    args.date,
                )
            )
        elif args.command == "work-append":
            emit(append_work_note(vault, args.kind, args.text, args.date))
        elif args.command == "github":
            emit(github_attention())
        elif args.command == "calendar-list":
            emit({"calendars": calendar_names()})
        elif args.command == "calendar-today":
            emit({"events": calendar_today()})
        elif args.command == "calendar-upcoming":
            emit({"events": calendar_upcoming(args.minutes)})
        elif args.command == "calendar-range":
            emit({"events": calendar_range(args.days)})
        elif args.command == "calendar-add":
            emit(
                add_calendar_event(
                    args.calendar,
                    args.title,
                    args.start,
                    args.duration,
                )
            )
        elif args.command == "agenda-delete":
            emit(
                delete_agenda_item(
                    vault,
                    args.kind,
                    args.calendar,
                    args.uid,
                    args.title,
                    args.ref,
                )
            )
        elif args.command == "reminder-list":
            emit({"reminders": list_reminders(vault, args.list)})
        elif args.command == "reminder-add":
            emit(create_reminder(args.list, args.title, args.date))
        elif args.command == "reminder-complete":
            emit(complete_reminder(vault, args.list, args.id))
        elif args.command == "reminder-update":
            emit(
                update_reminder(
                    vault,
                    args.list,
                    args.id,
                    args.title,
                    args.date,
                )
            )
        elif args.command == "mail":
            emit(
                {
                    "messages": mail_attention(
                        args.query,
                        args.unread_only,
                        args.account,
                    )
                }
            )
        elif args.command == "bookit-business":
            emit(bookit_business())
        elif args.command == "health-personal":
            emit(personal_health())
        elif args.command == "scratchpad-get":
            emit(scratchpad_get())
        elif args.command == "scratchpad-set":
            emit(scratchpad_set(args.content))
        elif args.command == "scratchpad-clear":
            emit(scratchpad_clear())
        elif args.command == "audit-list":
            emit({"events": audit_list(args.limit)})
        elif args.command == "sync-status":
            emit(cloud_sync_status())
        elif args.command == "snapshot-list":
            emit({"snapshots": daily_snapshot_list()})
        elif args.command == "snapshot-get":
            emit(daily_snapshot_get(args.date))
        elif args.command == "render-logs":
            emit(
                render_logs(
                    vault,
                    args.name,
                    args.limit,
                    args.level,
                    args.text,
                )
            )
        elif args.command == "resend-emails":
            emit(resend_activity(vault, args.name, args.limit))
        elif args.command == "weekly-review":
            emit(weekly_review(vault))
        elif args.command == "dashboard":
            emit(dashboard(vault))
        elif args.command == "exceptions":
            emit(exception_center(vault))
        elif args.command == "daily-rollover":
            emit(daily_rollover(vault, args.date))
        elif args.command == "daily-tasks":
            emit(
                list_daily_tasks(
                    vault,
                    args.date,
                    args.include_completed,
                )
            )
        elif args.command == "home":
            emit(
                home(
                    vault,
                    args.include_personal,
                    args.include_work,
                    not args.morning_only,
                )
            )
        else:
            parser.error(f"Unknown command: {args.command}")
    except CommandCenterError as exc:
        details = exc.args[1] if len(exc.args) > 1 else None
        fail(str(exc.args[0]), details=details)
    except OSError as exc:
        fail(f"Filesystem operation failed: {exc}")


if __name__ == "__main__":
    main()
