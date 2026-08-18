#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


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
STATE = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Command Center"
    / "call-reminders.json"
)
MEET_PATTERN = re.compile(
    r"https://(?:meet\.google\.com|[^/\s]+\.zoom\.us|"
    r"teams\.microsoft\.com|teams\.live\.com)/[^\s<>\"]+",
    re.IGNORECASE,
)


def upcoming_events() -> list[dict[str, str]]:
    result = subprocess.run(
        [sys.executable, str(COMMAND), "calendar-upcoming", "--minutes", "15"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)["events"]


def load_state() -> dict[str, str]:
    if not STATE.is_file():
        return {}
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot read call reminder state: {STATE}") from exc
    if not isinstance(state, dict):
        raise RuntimeError(f"Call reminder state is not an object: {STATE}")
    return {str(key): str(value) for key, value in state.items()}


def save_state(state: dict[str, str]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(STATE)


def event_key(event: dict[str, str]) -> str:
    value = "\0".join(
        event.get(field, "")
        for field in ("calendar", "title", "start")
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def meeting_link(event: dict[str, str]) -> str:
    source = " ".join(
        value
        for value in (event.get("url", ""), event.get("description", ""))
        if value
    )
    match = MEET_PATTERN.search(source)
    return match.group(0) if match else ""


def main() -> None:
    now = datetime.now().astimezone()
    cutoff = now - timedelta(days=2)
    state = {
        key: timestamp
        for key, timestamp in load_state().items()
        if datetime.fromisoformat(timestamp).astimezone() >= cutoff
    }
    for event in upcoming_events():
        key = event_key(event)
        if key in state:
            continue
        start = datetime.fromisoformat(event["start"]).astimezone()
        link = meeting_link(event)
        subprocess.run(
            [
                str(NOTIFIER),
                "--call",
                event["title"],
                start.strftime("%H:%M"),
                link,
            ],
            check=True,
        )
        state[key] = now.isoformat(timespec="seconds")
    save_state(state)


if __name__ == "__main__":
    main()
