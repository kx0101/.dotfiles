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
JOBS = (
    ("com.command-center.cloud-sync", "commands", 10, "cloud-sync"),
    ("com.command-center.cloud-snapshot", "snapshot", 60, "cloud-snapshot"),
    (
        "com.command-center.cloud-enrichment",
        "enrichment",
        600,
        "cloud-enrichment",
    ),
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
    domain = f"gui/{os.getuid()}"
    for label, _, _, _ in JOBS:
        path = LAUNCH_AGENTS / f"{label}.plist"
        subprocess.run(
            ["launchctl", "bootout", domain, str(path)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    subprocess.run(
        [PYTHON, str(ROOT / "cloud_sync.py"), "--mode", "enrichment"],
        check=True,
        env={**os.environ, "PATH": EXECUTABLE_PATH},
    )
    for label, mode, interval, log_name in JOBS:
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
    <string>{ROOT / "cloud_sync.py"}</string>
    <string>--mode</string>
    <string>{mode}</string>
  </array>
  <key>StartInterval</key>
  <integer>{interval}</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>{EXECUTABLE_PATH}</string>
  </dict>
  <key>StandardOutPath</key>
  <string>{LOGS / f"{log_name}.log"}</string>
  <key>StandardErrorPath</key>
  <string>{LOGS / f"{log_name}.error.log"}</string>
</dict>
</plist>
""",
            encoding="utf-8",
        )
        subprocess.run(["launchctl", "bootstrap", domain, str(path)], check=True)
    print(
        "Installed Command Center cloud jobs: commands 10s, "
        "snapshot 60s, enrichment 600s."
    )


if __name__ == "__main__":
    main()
