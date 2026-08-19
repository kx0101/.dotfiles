from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable


def task_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": str(item.get("title") or ""),
        "display": str(item.get("title") or ""),
        "depth": len(item.get("parent_path") or []),
        "completed": bool(item.get("completed")),
    }


def agenda_item(item: dict[str, Any]) -> dict[str, Any]:
    if item.get("all_day") == "true":
        time_label = "Ολοήμερο"
    else:
        try:
            time_label = datetime.fromisoformat(str(item["start"])).strftime("%H:%M")
        except (KeyError, ValueError):
            time_label = str(item.get("start") or "")
    title = str(item.get("title") or "")
    calendar = str(item.get("calendar") or "")
    meta = " · ".join(value for value in (time_label, calendar) if value)
    return {
        "title": title,
        "display": f"{time_label} · {title}" if time_label else title,
        "meta": meta,
        "depth": 0,
        "completed": bool(item.get("completed")),
    }


def reminder_item(item: dict[str, Any]) -> dict[str, Any]:
    title = str(item.get("title") or "")
    due = str(item.get("due") or item.get("start") or "")
    return {
        "title": title,
        "display": title,
        "meta": due,
        "depth": 0,
        "completed": bool(item.get("completed")),
    }


def section(
    key: str,
    title: str,
    items: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    return {"key": key, "title": title, "items": list(items)}


def build_daily_briefing(
    *,
    selected_date: str,
    personal: list[dict[str, Any]],
    work: list[dict[str, Any]],
    agenda: list[dict[str, Any]],
    reminders: list[dict[str, Any]],
    overdue: list[dict[str, Any]] | None = None,
    errors: dict[str, str] | None = None,
) -> dict[str, Any]:
    error_items = [
        {
            "title": name,
            "display": f"{name}: {message}",
            "depth": 0,
            "completed": False,
        }
        for name, message in (errors or {}).items()
    ]
    return {
        "kind": "daily",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "selected_date": selected_date,
        "timezone": "Europe/Athens",
        "sections": [
            section("overdue", "Εκπρόθεσμα", map(task_item, overdue or [])),
            section(
                "agenda",
                "Πρόγραμμα",
                (
                    agenda_item(item)
                    for item in agenda
                    if item.get("kind") != "reminder"
                ),
            ),
            section(
                "reminders",
                "Υπενθυμίσεις",
                map(reminder_item, reminders),
            ),
            section(
                "personal",
                "Προσωπικά",
                (task_item(item) for item in personal if not item.get("completed")),
            ),
            section(
                "work",
                "Δουλειά",
                (task_item(item) for item in work if not item.get("completed")),
            ),
            section("errors", "Σφάλματα integrations", error_items),
        ],
    }


def render_markdown(contract: dict[str, Any], heading: str) -> str:
    lines = [heading, ""]
    for section_value in contract["sections"]:
        lines.append(f"## {section_value['title']}")
        items = section_value["items"]
        if not items:
            lines.append("- Κανένα.")
            continue
        for item in items:
            prefix = "  " * min(int(item.get("depth") or 0), 8)
            lines.append(f"{prefix}- {item.get('display') or item.get('title')}")
    return "\n".join(lines) + "\n"
