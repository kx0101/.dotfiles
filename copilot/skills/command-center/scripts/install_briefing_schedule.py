#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
LOGS = Path.home() / "Library" / "Logs" / "CommandCenter"
PYTHON = os.environ.get("COMMAND_CENTER_PYTHON", sys.executable)


def plist(label: str, kind: str, hour: int, weekday: int | None = None) -> str:
    calendar = f"""        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>30</integer>"""
    if weekday is not None:
        calendar += f"""
        <key>Weekday</key>
        <integer>{weekday}</integer>"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{PYTHON}</string>
    <string>{ROOT / "briefing_scheduler.py"}</string>
    <string>{kind}</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
{calendar}
  </dict>
  <key>StandardOutPath</key>
  <string>{LOGS / (kind + ".log")}</string>
  <key>StandardErrorPath</key>
  <string>{LOGS / (kind + ".error.log")}</string>
</dict>
</plist>
"""


def install(label: str, kind: str, weekday: int | None) -> None:
    path = LAUNCH_AGENTS / f"{label}.plist"
    path.write_text(plist(label, kind, 8, weekday), encoding="utf-8")
    domain = f"gui/{os.getuid()}"
    subprocess.run(
        ["launchctl", "bootout", domain, str(path)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(["launchctl", "bootstrap", domain, str(path)], check=True)


def main() -> None:
    LAUNCH_AGENTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    install("com.command-center.briefing-morning", "morning", None)
    install("com.command-center.briefing-weekly", "weekly", 2)
    print("Installed Command Center briefings: daily 08:30, Monday 08:30.")


if __name__ == "__main__":
    main()
