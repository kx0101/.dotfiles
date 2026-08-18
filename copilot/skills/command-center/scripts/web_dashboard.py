#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
COMMAND = ROOT / "command_center.py"
WEB_ROOT = ROOT.parent / "web"
SHARED_STYLES = ROOT.parent / "cloud" / "src" / "style.css"
ASSETS = {
    "/": (WEB_ROOT / "index.html", "text/html; charset=utf-8"),
    "/app.js": (WEB_ROOT / "app.js", "text/javascript; charset=utf-8"),
    "/styles.css": (SHARED_STYLES, "text/css; charset=utf-8"),
}
COMMANDS = {
    "/api/tasks": ("daily-tasks", "--include-completed"),
    "/api/agenda": ("calendar-today",),
    "/api/health": ("project-health",),
    "/api/projects": ("project-list",),
    "/api/mail": (
        "mail",
        "--account",
        "liakos.koulaxis@yahoo.com",
    ),
    "/api/learning": ("learning-list",),
    "/api/reminders": ("reminder-list", "--list", "Reminders"),
    "/api/calendars": ("calendar-list",),
    "/api/apple-health": ("health-personal",),
    "/api/scratchpad": ("scratchpad-get",),
    "/api/sync-status": ("sync-status",),
    "/api/audit": ("audit-list", "--limit", "100"),
    "/api/snapshots": ("snapshot-list",),
}


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "CommandCenterDashboard/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/project":
            names = parse_qs(parsed.query).get("name", [])
            if len(names) != 1 or not names[0].strip() or len(names[0]) > 100:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "A valid project name is required."},
                )
                return
            self._serve_command(("project-status", "--name", names[0].strip()))
            return
        if path in {"/api/project/business", "/api/project/emails"}:
            names = parse_qs(parsed.query).get("name", [])
            if len(names) != 1 or names[0].casefold() != "bookit":
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "Business details are currently available for BookIt."},
                )
                return
            command = (
                ("bookit-business",)
                if path.endswith("/business")
                else ("resend-emails", "--name", "BookIt", "--limit", "5")
            )
            self._serve_command(command)
            return
        if path == "/api/search":
            queries = parse_qs(parsed.query).get("q", [])
            if len(queries) != 1 or not 2 <= len(queries[0].strip()) <= 200:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "Search query must contain 2-200 characters."},
                )
                return
            self._serve_command(
                ("search", "--query", queries[0].strip(), "--limit", "50")
            )
            return
        if path == "/api/snapshot":
            dates = parse_qs(parsed.query).get("date", [])
            if len(dates) != 1 or len(dates[0]) != 10:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "A valid snapshot date is required."},
                )
                return
            self._serve_command(("snapshot-get", "--date", dates[0]))
            return
        if path in COMMANDS:
            self._serve_command(COMMANDS[path])
            return
        if path in ASSETS:
            self._serve_asset(*ASSETS[path])
            return
        self._send_json(
            HTTPStatus.NOT_FOUND,
            {"error": "Not found."},
        )

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        allowed_paths = {
            "/api/task/add",
            "/api/task/complete",
            "/api/task/reopen",
            "/api/task/update",
            "/api/learning/add",
            "/api/learning/complete",
            "/api/reminder/add",
            "/api/reminder/complete",
            "/api/reminder/update",
            "/api/capture",
            "/api/calendar/add",
            "/api/scratchpad",
        }
        if path not in allowed_paths:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return
        expected_origin = (
            f"http://127.0.0.1:{self.server.server_address[1]}"
        )
        if (
            self.headers.get("Origin") != expected_origin
            or self.headers.get("X-Command-Center") != "1"
            or self.headers.get_content_type() != "application/json"
        ):
            self._send_json(
                HTTPStatus.FORBIDDEN,
                {"error": "Dashboard write request was rejected."},
            )
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        maximum_length = 24_000 if path == "/api/scratchpad" else 4096
        if length < 1 or length > maximum_length:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Invalid request body length."},
            )
            return
        try:
            payload = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Request body must be valid JSON."},
            )
            return
        if not isinstance(payload, dict):
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Request body must be an object."},
            )
            return
        if path == "/api/scratchpad":
            action = str(payload.get("action") or "")
            if action == "clear":
                self._serve_command(("scratchpad-clear",))
                return
            content = payload.get("content")
            if (
                action != "save"
                or not isinstance(content, str)
                or len(content) > 20_000
            ):
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "Invalid Scratchpad data."},
                )
                return
            self._serve_command(("scratchpad-set", "--content", content))
            return
        if path == "/api/learning/complete":
            identifier = str(payload.get("id") or "").strip()
            if not identifier or len(identifier) > 100:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "A valid Learning item ID is required."},
                )
                return
            self._serve_command(("learning-complete", "--query", identifier))
            return
        if path == "/api/reminder/complete":
            identifier = str(payload.get("id") or "").strip()
            if not identifier or len(identifier) > 500:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "A valid Reminder ID is required."},
                )
                return
            self._serve_command(
                (
                    "reminder-complete",
                    "--list",
                    "Reminders",
                    "--id",
                    identifier,
                )
            )
            return

        title = str(payload.get("title") or "").strip()
        if path == "/api/reminder/update":
            identifier = str(payload.get("id") or "").strip()
            reminder_date = str(payload.get("date") or "").strip()
            if (
                not identifier
                or len(identifier) > 500
                or not title
                or len(title) > 300
                or len(reminder_date) != 10
            ):
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "Valid Reminder update data is required."},
                )
                return
            self._serve_command(
                (
                    "reminder-update",
                    "--list",
                    "Reminders",
                    "--id",
                    identifier,
                    "--title",
                    title,
                    "--date",
                    reminder_date,
                )
            )
            return
        if path == "/api/calendar/add":
            calendar = str(payload.get("calendar") or "").strip()
            start = str(payload.get("start") or "").strip()
            try:
                duration = int(payload.get("duration"))
            except (TypeError, ValueError):
                duration = 0
            if (
                not title
                or len(title) > 300
                or not calendar
                or len(calendar) > 200
                or len(start) != 16
                or duration < 5
                or duration > 480
            ):
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "Valid calendar event data is required."},
                )
                return
            self._serve_command(
                (
                    "calendar-add",
                    "--calendar",
                    calendar,
                    "--title",
                    title,
                    "--start",
                    start,
                    "--duration",
                    str(duration),
                )
            )
            return

        if path == "/api/capture":
            capture_kind = str(payload.get("kind") or "")
            capture_date = str(payload.get("date") or "").strip()
            project = str(payload.get("project") or "").strip()
            url = str(payload.get("url") or "").strip()
            valid_kinds = {
                "personal-task",
                "work-task",
                "reminder",
                "book",
                "article",
                "video",
                "project-note",
            }
            if (
                not title
                or len(title) > 1000
                or capture_kind not in valid_kinds
                or (capture_date and len(capture_date) != 10)
                or len(project) > 100
                or len(url) > 2000
            ):
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "Invalid capture data."},
                )
                return
            if capture_kind == "personal-task":
                command = ["task-add", "--title", title, "--area", "Personal"]
                if capture_date:
                    command.extend(["--date", capture_date])
            elif capture_kind == "work-task":
                command = (
                    ["work-task-add", "--title", title, "--date", capture_date]
                    if capture_date
                    else ["task-add", "--title", title, "--area", "Work"]
                )
            elif capture_kind == "reminder":
                command = [
                    "reminder-add",
                    "--list",
                    "Reminders",
                    "--title",
                    title,
                ]
                if capture_date:
                    command.extend(["--date", capture_date])
            elif capture_kind in {"book", "article", "video"}:
                command = [
                    "learning-add",
                    "--title",
                    title,
                    "--kind",
                    capture_kind,
                    "--source",
                    "Command Center dashboard",
                ]
                if url:
                    command.extend(["--url", url])
                if project:
                    command.extend(["--project", project])
            else:
                if not project:
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "Project note capture requires a project."},
                    )
                    return
                command = [
                    "project-record",
                    "--name",
                    project,
                    "--kind",
                    "note",
                    "--text",
                    title,
                    "--source",
                    "Command Center dashboard",
                ]
            self._serve_command(tuple(command))
            return

        if path == "/api/reminder/add":
            reminder_date = str(payload.get("date") or "").strip()
            if (
                not title
                or len(title) > 300
                or (reminder_date and len(reminder_date) != 10)
            ):
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "A valid Reminder title is required."},
                )
                return
            command = [
                "reminder-add",
                "--list",
                "Reminders",
                "--title",
                title,
            ]
            if reminder_date:
                command.extend(["--date", reminder_date])
            self._serve_command(tuple(command))
            return

        if path == "/api/learning/add":
            kind = str(payload.get("kind") or "")
            url = str(payload.get("url") or "").strip()
            if (
                not title
                or len(title) > 300
                or kind not in {"book", "article", "video"}
                or len(url) > 2000
            ):
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "Valid title and Learning category are required."},
                )
                return
            command = [
                "learning-add",
                "--title",
                title,
                "--kind",
                kind,
                "--source",
                "Command Center dashboard",
            ]
            if url:
                command.extend(["--url", url])
            self._serve_command(tuple(command))
            return

        area = str(payload.get("area") or "")
        task_date = str(payload.get("date") or "")
        current_date = str(payload.get("current_date") or task_date)
        if (
            not title
            or len(title) > 300
            or area not in {"Personal", "Work"}
            or len(task_date) != 10
        ):
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Valid title, area, and date are required."},
            )
            return
        if path == "/api/task/add":
            command = (
                ("task-add", "--title", title, "--area", "Personal", "--date", task_date)
                if area == "Personal"
                else ("work-task-add", "--title", title, "--date", task_date)
            )
        elif path in {"/api/task/complete", "/api/task/reopen"}:
            command_name = (
                "task-complete"
                if area == "Personal" and path.endswith("/complete")
                else "task-reopen"
                if area == "Personal"
                else "work-task-complete"
                if path.endswith("/complete")
                else "work-task-reopen"
            )
            command = (
                command_name,
                "--query",
                title,
                "--date",
                task_date,
            )
        else:
            command = (
                (
                    "task-update",
                    "--query",
                    str(payload.get("old_title") or title),
                    "--current-date",
                    current_date,
                    "--title",
                    title,
                    "--date",
                    task_date,
                )
                if area == "Personal"
                else (
                    "work-task-update",
                    "--query",
                    str(payload.get("old_title") or title),
                    "--current-date",
                    current_date,
                    "--title",
                    title,
                    "--date",
                    task_date,
                )
            )
        self._serve_command(command)

    def log_message(self, format: str, *args: object) -> None:
        print(
            f"{self.address_string()} - {format % args}",
            file=sys.stderr,
        )

    def _security_headers(self) -> None:
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")

    def _serve_command(self, arguments: tuple[str, ...]) -> None:
        try:
            result = subprocess.run(
                [sys.executable, str(COMMAND), *arguments],
                check=False,
                capture_output=True,
                text=True,
                timeout=180,
                env={**os.environ, "COMMAND_CENTER_SOURCE": "local-web"},
            )
        except subprocess.TimeoutExpired:
            self._send_json(
                HTTPStatus.GATEWAY_TIMEOUT,
                {"error": "Command Center timed out."},
            )
            return
        stream = result.stdout if result.returncode == 0 else result.stderr
        try:
            payload = json.loads(stream)
        except json.JSONDecodeError:
            self._send_json(
                HTTPStatus.BAD_GATEWAY,
                {"error": "Command Center returned malformed JSON."},
            )
            return
        self._send_json(
            HTTPStatus.OK if result.returncode == 0 else HTTPStatus.BAD_GATEWAY,
            payload,
        )

    def _serve_asset(self, path: Path, content_type: str) -> None:
        try:
            content = path.read_bytes()
        except OSError:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"Dashboard asset is missing: {path.name}"},
            )
            return
        self.send_response(HTTPStatus.OK)
        self._security_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        try:
            self.wfile.write(content)
        except BrokenPipeError:
            return

    def _send_json(self, status: HTTPStatus, payload: object) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._security_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        try:
            self.wfile.write(content)
        except BrokenPipeError:
            return


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Command Center dashboard")
    parser.add_argument("--port", type=int, default=4317)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    if args.port < 1024 or args.port > 65535:
        parser.error("port must be between 1024 and 65535")

    address = ("127.0.0.1", args.port)
    server = ThreadingHTTPServer(address, DashboardHandler)
    url = f"http://{address[0]}:{address[1]}"
    print(f"Command Center dashboard: {url}")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
