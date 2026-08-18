#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
LOGS = Path.home() / "Library" / "Logs" / "CommandCenter"
LABEL = "com.command-center.dashboard"
PORT = 4317
PYTHON = os.environ.get("COMMAND_CENTER_PYTHON", sys.executable)
EXECUTABLE_PATH = (
    "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
)


def main() -> None:
    LAUNCH_AGENTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    path = LAUNCH_AGENTS / f"{LABEL}.plist"
    path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{PYTHON}</string>
    <string>{ROOT / "web_dashboard.py"}</string>
    <string>--no-open</string>
    <string>--port</string>
    <string>{PORT}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>{EXECUTABLE_PATH}</string>
  </dict>
  <key>StandardOutPath</key>
  <string>{LOGS / "dashboard.log"}</string>
  <key>StandardErrorPath</key>
  <string>{LOGS / "dashboard.error.log"}</string>
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

    url = f"http://127.0.0.1:{PORT}"
    for _ in range(30):
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    print(f"Installed Command Center dashboard: {url}")
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.2)
    raise RuntimeError(
        f"Dashboard did not become ready. Check {LOGS / 'dashboard.error.log'}."
    )


if __name__ == "__main__":
    main()
