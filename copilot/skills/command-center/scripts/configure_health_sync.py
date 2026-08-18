#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import secrets
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOUD = ROOT.parent / "cloud"


def keychain(service: str) -> str:
    return subprocess.run(
        ["security", "find-generic-password", "-s", service, "-w"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def publishable_key() -> str:
    path = CLOUD / ".env.local"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("VITE_SUPABASE_ANON_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("VITE_SUPABASE_ANON_KEY is missing from cloud/.env.local.")


def main() -> None:
    base_url = keychain("command-center-supabase-url").rstrip("/")
    service_key = keychain("command-center-supabase-service")
    user_id = keychain("command-center-supabase-user")
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    request = urllib.request.Request(
        f"{base_url}/rest/v1/command_center_health_ingest_tokens"
        "?on_conflict=user_id",
        data=json.dumps(
            {"user_id": user_id, "token_hash": token_hash}
        ).encode("utf-8"),
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30):
        pass
    subprocess.run(
        [
            "security",
            "add-generic-password",
            "-U",
            "-s",
            "command-center-health-ingest-token",
            "-a",
            "command-center",
            "-w",
            token,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    shortcut = {
        "url": f"{base_url}/rest/v1/rpc/ingest_command_center_health",
        "headers": {
            "apikey": publishable_key(),
            "Content-Type": "application/json",
        },
        "body_template": {
            "ingest_secret": token,
            "metric_day": "YYYY-MM-DD",
            "metric_steps": 0,
            "metric_sleep_minutes": 0,
            "metric_active_energy_kcal": 0,
            "metric_resting_heart_rate": 0,
        },
    }
    subprocess.run(
        ["pbcopy"],
        input=json.dumps(shortcut, ensure_ascii=False, indent=2),
        text=True,
        check=True,
    )
    print(
        "Configured health ingest token in Keychain and copied the Shortcut "
        "request template to the clipboard."
    )


if __name__ == "__main__":
    main()
