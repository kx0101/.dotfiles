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
EXECUTABLE_PATH = (
    "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
)
APP = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Command Center"
    / "CommandCenterNotifier.app"
)


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
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>{EXECUTABLE_PATH}</string>
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


def install_call_reminders() -> None:
    label = "com.command-center.call-reminders"
    path = LAUNCH_AGENTS / f"{label}.plist"
    path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{PYTHON}</string>
    <string>{ROOT / "upcoming_call_notifier.py"}</string>
  </array>
  <key>StartInterval</key>
  <integer>60</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>{EXECUTABLE_PATH}</string>
  </dict>
  <key>StandardOutPath</key>
  <string>{LOGS / "call-reminders.log"}</string>
  <key>StandardErrorPath</key>
  <string>{LOGS / "call-reminders.error.log"}</string>
</dict>
</plist>
""",
        encoding="utf-8",
    )
    domain = f"gui/{os.getuid()}"
    subprocess.run(
        ["launchctl", "bootout", domain, str(path)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(["launchctl", "bootstrap", domain, str(path)], check=True)


def install_notifier() -> None:
    executable = APP / "Contents" / "MacOS" / "CommandCenterNotifier"
    executable.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "swiftc",
            str(ROOT / "briefing_notifier.swift"),
            "-o",
            str(executable),
            "-framework",
            "AppKit",
            "-framework",
            "UserNotifications",
        ],
        check=True,
    )
    (APP / "Contents").joinpath("Info.plist").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleIdentifier</key>
  <string>com.command-center.notifier</string>
  <key>CFBundleName</key>
  <string>Command Center Notifier</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>LSUIElement</key>
  <true/>
</dict>
</plist>
""",
        encoding="utf-8",
    )
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(APP)], check=True)


def main() -> None:
    LAUNCH_AGENTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    install_notifier()
    install("com.command-center.briefing-morning", "morning", None)
    install("com.command-center.briefing-weekly", "weekly", 2)
    install_call_reminders()
    print(
        "Installed Command Center briefings and 15-minute timed-event reminders."
    )


if __name__ == "__main__":
    main()
