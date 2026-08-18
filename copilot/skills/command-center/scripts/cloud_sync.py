#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import fcntl
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
COMMAND = ROOT / "command_center.py"
LOCK_PATH = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Command Center"
    / "cloud-sync.lock"
)
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def keychain(service: str) -> str:
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service, "-w"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"Missing macOS Keychain service: {service}")
    return result.stdout.strip()


def configuration() -> tuple[str, str, str]:
    url = os.environ.get("COMMAND_CENTER_SUPABASE_URL") or keychain(
        "command-center-supabase-url"
    )
    service_key = os.environ.get(
        "COMMAND_CENTER_SUPABASE_SERVICE_KEY"
    ) or keychain("command-center-supabase-service")
    user_id = os.environ.get("COMMAND_CENTER_SUPABASE_USER_ID") or keychain(
        "command-center-supabase-user"
    )
    url = url.rstrip("/")
    if not url.startswith("https://") or not UUID_PATTERN.fullmatch(user_id):
        raise RuntimeError("Invalid Supabase URL or user ID.")
    return url, service_key, user_id


def run_cli(*arguments: str) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(COMMAND), *arguments],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "COMMAND_CENTER_SOURCE": "vercel"},
    )
    stream = result.stdout if result.returncode == 0 else result.stderr
    try:
        payload = json.loads(stream)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Command Center returned malformed JSON.") from exc
    if result.returncode != 0:
        raise RuntimeError(str(payload.get("error") or "Command Center failed."))
    return payload


def request_json(
    base_url: str,
    service_key: str,
    method: str,
    path: str,
    payload: Any = None,
    *,
    prefer: str | None = None,
) -> Any:
    body = (
        json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if payload is not None
        else None
    )
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    request = urllib.request.Request(
        f"{base_url}/rest/v1/{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Supabase returned HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(
            f"Supabase request failed: {type(exc).__name__}."
        ) from exc
    return json.loads(content) if content else None


def snapshot() -> dict[str, Any]:
    daily = run_cli("daily-tasks", "--include-completed")
    reminders = run_cli("reminder-list", "--list", "Reminders")
    learning = run_cli("learning-list")
    projects = run_cli("project-list")
    agenda = run_cli("calendar-today")
    calendar_plan = run_cli("calendar-range", "--days", "31")
    calendars = run_cli("calendar-list")
    system_health = run_cli("project-health")
    mail = run_cli(
        "mail",
        "--account",
        "liakos.koulaxis@yahoo.com",
    )
    github = run_cli("github")
    bookit_business = run_cli("bookit-business")
    bookit_emails = run_cli(
        "resend-emails",
        "--name",
        "BookIt",
        "--limit",
        "5",
    )
    audit = run_cli("audit-list", "--limit", "100")
    scratchpad = run_cli("scratchpad-get")
    today = datetime.now().astimezone().date()
    daily_plans: dict[str, Any] = {}
    for offset in range(1, 31):
        plan_date = (today + timedelta(days=offset)).isoformat()
        tasks = run_cli(
            "daily-tasks",
            "--date",
            plan_date,
            "--include-completed",
        )
        if tasks["personal"] or tasks["work"]:
            daily_plans[plan_date] = tasks
    sanitized_projects = []
    for project in projects["projects"]:
        if project["area"] != "personal":
            continue
        records = run_cli(
            "project-records",
            "--name",
            project["name"],
            "--kind",
            "note",
        )["records"]
        sanitized_projects.append(
            {
                "name": project["name"],
                "status": project["status"],
                "lifecycle": project["lifecycle"],
                "github": project["github"],
                "tasks": run_cli(
                "task-list",
                "--project",
                project["name"],
                "--view",
                "all",
                )["tasks"],
                "notes": [
                    {
                        "id": record["id"],
                        "timestamp": record["timestamp"],
                        "text": record["text"],
                        "source": record["source"],
                    }
                    for record in records
                    if record.get("active", True)
                ],
            }
        )
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "personal_tasks": daily["personal"],
        "work_tasks": daily["work"],
        "reminders": reminders["reminders"],
        "learning": learning["items"],
        "projects": sanitized_projects,
        "agenda": agenda["events"],
        "calendar_plan": calendar_plan["events"],
        "daily_plans": daily_plans,
        "calendars": calendars["calendars"],
        "system_health": system_health["checks"],
        "mail": mail["messages"],
        "github": github,
        "bookit_business": bookit_business,
        "bookit_emails": bookit_emails,
        "audit": audit["events"],
        "scratchpad": scratchpad,
    }


def push_snapshot(
    base_url: str,
    service_key: str,
    user_id: str,
) -> None:
    payload = snapshot()
    now = datetime.now().astimezone()
    request_json(
        base_url,
        service_key,
        "POST",
        "command_center_snapshots?on_conflict=user_id",
        {
            "user_id": user_id,
            "payload": payload,
            "updated_at": now.isoformat(timespec="seconds"),
        },
        prefer="resolution=merge-duplicates,return=minimal",
    )
    request_json(
        base_url,
        service_key,
        "POST",
        "command_center_daily_snapshots?on_conflict=user_id,day",
        {
            "user_id": user_id,
            "day": now.date().isoformat(),
            "payload": payload,
            "updated_at": now.isoformat(timespec="seconds"),
        },
        prefer="resolution=merge-duplicates,return=minimal",
    )


def command_arguments(command: dict[str, Any]) -> tuple[str, ...]:
    action = command["action"]
    payload = command["payload"]
    title = str(payload.get("title") or "").strip()
    task_date = str(payload.get("date") or "").strip()
    if action == "add-personal-task":
        arguments = ["task-add", "--title", title, "--area", "Personal"]
        if task_date:
            arguments.extend(["--date", task_date])
        if payload.get("parent_line") is not None:
            arguments.extend(["--parent-line", str(payload["parent_line"])])
        return tuple(arguments)
    if action == "add-work-task":
        arguments = [
            "work-task-add",
            "--title",
            title,
            "--date",
            task_date,
        ]
        if payload.get("parent_line") is not None:
            arguments.extend(["--parent-line", str(payload["parent_line"])])
        return tuple(arguments)
    if action == "add-reminder":
        arguments = [
            "reminder-add",
            "--list",
            "Reminders",
            "--title",
            title,
        ]
        if task_date:
            arguments.extend(["--date", task_date])
        return tuple(arguments)
    if action == "add-learning":
        kind = str(payload.get("kind") or "")
        if kind not in {"book", "article", "video"}:
            raise ValueError("Invalid Learning kind.")
        arguments = [
            "learning-add",
            "--title",
            title,
            "--kind",
            kind,
            "--source",
            "Command Center mobile",
        ]
        url = str(payload.get("url") or "").strip()
        if url:
            arguments.extend(["--url", url])
        return tuple(arguments)
    if action == "add-project-note":
        return (
            "project-record",
            "--name",
            str(payload.get("project") or ""),
            "--kind",
            "note",
            "--text",
            title,
            "--source",
            "Command Center Vercel",
        )
    if action == "archive-project-note":
        return (
            "project-record-archive",
            "--name",
            str(payload.get("project") or ""),
            "--id",
            str(payload.get("id") or ""),
            "--source",
            "Command Center Vercel",
        )
    if action == "delete-agenda-item":
        arguments = [
            "agenda-delete",
            "--kind",
            str(payload.get("kind") or ""),
            "--calendar",
            str(payload.get("calendar") or ""),
            "--uid",
            str(payload.get("uid") or ""),
            "--title",
            title,
        ]
        command_ref = str(payload.get("ref") or "")
        if command_ref:
            arguments.extend(["--ref", command_ref])
        return tuple(arguments)
    if action == "complete-personal-task":
        return (
            "task-complete",
            "--query",
            title,
            "--date",
            task_date,
        )
    if action == "complete-work-task":
        return (
            "work-task-complete",
            "--query",
            title,
            "--date",
            task_date,
        )
    if action == "reopen-personal-task":
        return (
            "task-reopen",
            "--query",
            title,
            "--date",
            task_date,
        )
    if action == "reopen-work-task":
        return (
            "work-task-reopen",
            "--query",
            title,
            "--date",
            task_date,
        )
    if action == "delete-personal-task":
        return (
            "task-delete",
            "--query",
            title,
            "--date",
            task_date,
        )
    if action == "delete-work-task":
        return (
            "work-task-delete",
            "--query",
            title,
            "--date",
            task_date,
        )
    if action == "update-personal-task":
        return (
            "task-update",
            "--query",
            str(payload.get("old_title") or ""),
            "--current-date",
            str(payload.get("current_date") or ""),
            "--title",
            title,
            "--date",
            task_date,
        )
    if action == "update-work-task":
        return (
            "work-task-update",
            "--query",
            str(payload.get("old_title") or ""),
            "--current-date",
            str(payload.get("current_date") or ""),
            "--title",
            title,
            "--date",
            task_date,
        )
    if action == "update-reminder":
        return (
            "reminder-update",
            "--list",
            "Reminders",
            "--id",
            str(payload.get("id") or ""),
            "--title",
            title,
            "--date",
            task_date,
        )
    if action == "add-calendar-event":
        return (
            "calendar-add",
            "--calendar",
            str(payload.get("calendar") or ""),
            "--title",
            title,
            "--start",
            str(payload.get("start") or ""),
            "--duration",
            str(payload.get("duration") or ""),
        )
    if action == "complete-reminder":
        return (
            "reminder-complete",
            "--list",
            "Reminders",
            "--id",
            str(payload.get("id") or ""),
        )
    if action == "complete-learning":
        return (
            "learning-complete",
            "--query",
            str(payload.get("id") or ""),
        )
    raise ValueError(f"Unsupported cloud action: {action}")


def update_command(
    base_url: str,
    service_key: str,
    command_id: str,
    status: str,
    result: dict[str, Any],
) -> None:
    request_json(
        base_url,
        service_key,
        "PATCH",
        f"command_center_commands?id=eq.{command_id}",
        {
            "status": status,
            "result": result,
            "processed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
        prefer="return=minimal",
    )


def process_commands(
    base_url: str,
    service_key: str,
    user_id: str,
) -> int:
    commands = request_json(
        base_url,
        service_key,
        "GET",
        "command_center_commands"
        f"?user_id=eq.{user_id}&status=eq.pending&order=created_at.asc&limit=20",
    )
    processed = 0
    for command in commands or []:
        command_id = str(command["id"])
        claimed = request_json(
            base_url,
            service_key,
            "PATCH",
            f"command_center_commands?id=eq.{command_id}&status=eq.pending",
            {"status": "processing"},
            prefer="return=representation",
        )
        if not claimed:
            continue
        try:
            result = run_cli(*command_arguments(command))
        except (KeyError, ValueError, RuntimeError, OSError) as exc:
            update_command(
                base_url,
                service_key,
                command_id,
                "failed",
                {"error": str(exc)[:500]},
            )
        else:
            update_command(
                base_url,
                service_key,
                command_id,
                "done",
                result,
            )
        processed += 1
    return processed


def main() -> None:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"processed": 0, "snapshot": "skipped_locked"}))
            return
        base_url, service_key, user_id = configuration()
        processed = process_commands(base_url, service_key, user_id)
        push_snapshot(base_url, service_key, user_id)
        print(json.dumps({"processed": processed, "snapshot": "updated"}))


if __name__ == "__main__":
    main()
