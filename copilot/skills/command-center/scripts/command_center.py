#!/usr/bin/env python3

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


TASKS_RELATIVE_PATH = Path("Command Center/Tasks.md")
PROJECTS_RELATIVE_PATH = Path("Command Center/Projects")
TASK_PATTERN = re.compile(r"^- \[(?P<state>[ xX])\] (?P<body>.+)$")
ACTION_DATE_PATTERN = re.compile(r"\s+📅\s+(?P<date>\d{4}-\d{2}-\d{2})")
COMPLETED_DATE_PATTERN = re.compile(r"\s+✅\s+(?P<date>\d{4}-\d{2}-\d{2})")
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
RECORD_KIND_LABELS = {
    "requirement": "Απαίτηση",
    "fact": "Πληροφορία",
    "idea": "Ιδέα",
    "decision": "Απόφαση",
    "note": "Σημείωση",
    "summary": "Ενημέρωση σύνοψης",
}
RECORD_LABEL_KINDS = {label: kind for kind, label in RECORD_KIND_LABELS.items()}


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
    line_number: int
    relation: str


@dataclass
class Project:
    name: str
    area: str
    status: str
    local_path: str | None
    github: str | None
    render_services: list[str]
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
        action_date = action_match.group("date") if action_match else None
        completed_date = completed_match.group("date") if completed_match else None
        title = ACTION_DATE_PATTERN.sub("", body)
        title = COMPLETED_DATE_PATTERN.sub("", title).strip()
        completed = match.group("state").lower() == "x"
        tasks.append(
            Task(
                title=title,
                section=section,
                completed=completed,
                action_date=action_date,
                completed_date=completed_date,
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
                local_path=data.get("local_path") or None,
                github=data.get("github") or None,
                render_services=list(data.get("render_services") or []),
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


def add_task(
    vault: Path,
    title: str,
    area: str | None,
    project: str | None,
    action_date: str | None,
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

    if project:
        section = project_by_name(vault, project).name
    elif area:
        section = area.title()
    else:
        section = "Inbox"

    tasks_path = vault / TASKS_RELATIVE_PATH
    with path_lock(tasks_path):
        tasks_path = ensure_tasks_file(vault)
        ensure_task_section(tasks_path, section)
        line = f"- [ ] {title}"
        if action_date:
            line += f" 📅 {action_date}"
        append_task(tasks_path, section, line)
    return {
        "title": title,
        "section": section,
        "action_date": action_date,
        "status": "open",
    }


def task_matches(tasks: list[Task], query: str) -> list[Task]:
    normalized = " ".join(query.split()).casefold()
    open_tasks = [task for task in tasks if not task.completed]
    exact = [task for task in open_tasks if task.title.casefold() == normalized]
    if exact:
        return exact
    return [task for task in open_tasks if normalized in task.title.casefold()]


def select_task(tasks_path: Path, query: str) -> Task:
    matches = task_matches(parse_tasks(tasks_path), query)
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


def complete_task(vault: Path, query: str) -> dict[str, Any]:
    tasks_path = vault / TASKS_RELATIVE_PATH
    with path_lock(tasks_path):
        task = select_task(tasks_path, query)
        completed_date = date.today().isoformat()
        line = f"- [x] {task.title}"
        if task.action_date:
            line += f" 📅 {task.action_date}"
        line += f" ✅ {completed_date}"
        replace_task_line(tasks_path, task, line)
    return {
        "title": task.title,
        "section": task.section,
        "status": "completed",
        "completed_date": completed_date,
    }


def reschedule_task(vault: Path, query: str, action_date: str) -> dict[str, Any]:
    validate_iso_date(action_date)
    tasks_path = vault / TASKS_RELATIVE_PATH
    with path_lock(tasks_path):
        task = select_task(tasks_path, query)
        line = f"- [ ] {task.title} 📅 {action_date}"
        replace_task_line(tasks_path, task, line)
    return {
        "title": task.title,
        "section": task.section,
        "status": "open",
        "action_date": action_date,
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
    ]
    if project.local_path:
        lines.append(f"local_path: {scalar(project.local_path)}")
    if project.github:
        lines.append(f"github: {scalar(project.github)}")
    lines.append("render_services:")
    lines.extend(f"  - {scalar(name)}" for name in project.render_services)
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
    return record


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


def add_project(
    vault: Path,
    name: str | None,
    area: str,
    local_path: str | None,
    github: str | None,
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
            local_path=portable_path(resolved_path) if resolved_path else None,
            github=discovered_github,
            render_services=services,
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
    items: list[dict[str, str]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        values = line.split("\t")
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


def calendar_today() -> list[dict[str, str]]:
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
            set eventLine to my cleanText(calName) & tab & my cleanText(summary of evt) & tab & my isoDate(start date of evt) & tab & my isoDate(end date of evt) & tab & (allday event of evt as text)
            set end of output to eventLine
        end repeat
    end repeat
end tell
set AppleScript's text item delimiters to linefeed
return output as text
'''
    events = parse_tabular_output(
        run_osascript(script),
        ["calendar", "title", "start", "end", "all_day"],
    )
    events.sort(key=lambda event: (event["start"], event["calendar"], event["title"]))
    return events


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
    return {
        "calendar": calendar,
        "title": title,
        "start": start,
        "duration_minutes": duration,
        "uid": uid,
    }


def mail_attention(query: str | None) -> list[dict[str, str]]:
    script = APPLE_SCRIPT_HELPERS + r'''
on run argv
    set searchQuery to ""
    if (count of argv) > 0 then set searchQuery to item 1 of argv
    set cutoffDate to (current date) - (48 * hours)
    set output to {}
    tell application "Mail"
        if searchQuery is "" then
            set matchingMessages to every message of inbox whose ((read status is false and date received > cutoffDate) or flagged status is true)
        else
            set matchingMessages to every message of inbox whose (subject contains searchQuery or sender contains searchQuery)
        end if
        set itemCount to count of matchingMessages
        if itemCount > 100 then set itemCount to 100
        repeat with i from 1 to itemCount
            set msg to item i of matchingMessages
            set messageLine to my cleanText(sender of msg) & tab & my cleanText(subject of msg) & tab & my isoDate(date received of msg) & tab & (read status of msg as text) & tab & (flagged status of msg as text)
            set end of output to messageLine
        end repeat
    end tell
    set AppleScript's text item delimiters to linefeed
    return output as text
end run
'''
    messages = parse_tabular_output(
        run_osascript(script, [query] if query else None),
        ["sender", "subject", "received", "read", "flagged"],
    )
    messages.sort(key=lambda message: message["received"], reverse=True)
    return messages[: 30 if query else 10]


def dashboard(vault: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "tasks": list_tasks(vault, "action", None),
        "github": None,
        "calendar": None,
        "mail": None,
        "errors": {},
    }
    integrations = {
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

    task_complete = commands.add_parser("task-complete")
    task_complete.add_argument("--query", required=True)

    task_reschedule = commands.add_parser("task-reschedule")
    task_reschedule.add_argument("--query", required=True)
    task_reschedule.add_argument("--date", required=True)

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
    summary_parser = commands.add_parser("project-summary-set")
    summary_parser.add_argument("--name", required=True)
    summary_parser.add_argument("--text", required=True)
    summary_parser.add_argument("--source", required=True)
    project_add = commands.add_parser("project-add")
    project_add.add_argument("--name")
    project_add.add_argument("--path")
    project_add.add_argument("--github")
    project_add.add_argument("--area", choices=["personal", "work"], default="personal")

    commands.add_parser("github")
    commands.add_parser("calendar-list")
    commands.add_parser("calendar-today")
    calendar_add = commands.add_parser("calendar-add")
    calendar_add.add_argument("--calendar", required=True)
    calendar_add.add_argument("--title", required=True)
    calendar_add.add_argument("--start", required=True)
    calendar_add.add_argument("--duration", type=int, default=60)

    mail = commands.add_parser("mail")
    mail.add_argument("--query")
    commands.add_parser("dashboard")
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
                )
            )
        elif args.command == "task-complete":
            emit(complete_task(vault, args.query))
        elif args.command == "task-reschedule":
            emit(reschedule_task(vault, args.query, args.date))
        elif args.command == "project-list":
            emit({"projects": [asdict(project) for project in load_projects(vault)]})
        elif args.command == "project-status":
            emit(project_status(vault, args.name))
        elif args.command == "project-records":
            records = project_records(project_note(vault, args.name))
            if args.kind:
                records = [record for record in records if record.kind == args.kind]
            emit({"records": [asdict(record) for record in records]})
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
                        args.path,
                        args.github,
                    )
                )
            )
        elif args.command == "github":
            emit(github_attention())
        elif args.command == "calendar-list":
            emit({"calendars": calendar_names()})
        elif args.command == "calendar-today":
            emit({"events": calendar_today()})
        elif args.command == "calendar-add":
            emit(
                add_calendar_event(
                    args.calendar,
                    args.title,
                    args.start,
                    args.duration,
                )
            )
        elif args.command == "mail":
            emit({"messages": mail_attention(args.query)})
        elif args.command == "dashboard":
            emit(dashboard(vault))
        else:
            parser.error(f"Unknown command: {args.command}")
    except CommandCenterError as exc:
        details = exc.args[1] if len(exc.args) > 1 else None
        fail(str(exc.args[0]), details=details)
    except OSError as exc:
        fail(f"Filesystem operation failed: {exc}")


if __name__ == "__main__":
    main()
