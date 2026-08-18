#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
LOGS = Path.home() / "Library" / "Logs" / "CommandCenter"
LABEL = "com.command-center.cloud-sync"
PYTHON = os.environ.get("COMMAND_CENTER_PYTHON", sys.executable)
EXECUTABLE_PATH = (
    "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
)


def require_keychain(service: str) -> None:
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service, "-w"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Missing Keychain service '{service}'. Run configure_cloud_sync.py."
        )


def main() -> None:
    for service in (
        "command-center-supabase-url",
        "command-center-supabase-user",
        "command-center-supabase-service",
    ):
        require_keychain(service)
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
    <string>{ROOT / "cloud_sync.py"}</string>
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
  <string>{LOGS / "cloud-sync.log"}</string>
  <key>StandardErrorPath</key>
  <string>{LOGS / "cloud-sync.error.log"}</string>
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
    print("Installed Command Center cloud sync: every 60 seconds.")


if __name__ == "__main__":
    main()
