#!/usr/bin/env python3

from __future__ import annotations

import argparse
import getpass
import subprocess


def store(service: str, value: str) -> None:
    subprocess.run(
        [
            "security",
            "add-generic-password",
            "-U",
            "-s",
            service,
            "-a",
            "command-center",
            "-w",
            value,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure Command Center cloud sync")
    parser.add_argument("--url", required=True)
    parser.add_argument("--user-id", required=True)
    args = parser.parse_args()
    service_key = getpass.getpass("Supabase service role key: ")
    if not service_key:
        parser.error("service role key is required")
    store("command-center-supabase-url", args.url)
    store("command-center-supabase-user", args.user_id)
    store("command-center-supabase-service", service_key)
    print("Stored Command Center Supabase configuration in macOS Keychain.")


if __name__ == "__main__":
    main()
