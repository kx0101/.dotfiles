# Command reference

Run from this skill directory:

```bash
python3 scripts/command_center.py <command> [options]
```

Every command returns JSON. Validation, integration, filesystem, and argument
errors are written to stderr as JSON and exit non-zero.

## Dashboard and reads

```bash
python3 scripts/command_center.py dashboard
python3 scripts/command_center.py exceptions
python3 scripts/command_center.py home
python3 scripts/command_center.py home --include-personal --include-work
python3 scripts/command_center.py home \
  --include-personal --include-work --morning-only
python3 scripts/command_center.py daily-rollover
python3 scripts/command_center.py daily-tasks
python3 scripts/command_center.py task-list --view action
python3 scripts/command_center.py task-list --view today
python3 scripts/command_center.py task-list --view overdue
python3 scripts/command_center.py task-list --view inbox
python3 scripts/command_center.py task-list --view week
python3 scripts/command_center.py task-list --view all
python3 scripts/command_center.py task-list --project BookIt
python3 scripts/command_center.py work-briefing
python3 scripts/command_center.py project-health
python3 scripts/command_center.py weekly-review
python3 scripts/command_center.py github
python3 scripts/command_center.py calendar-today
python3 scripts/command_center.py calendar-upcoming --minutes 15
python3 scripts/command_center.py calendar-range --days 14
python3 scripts/command_center.py reminder-list
python3 scripts/command_center.py reminder-add \
  --title "Να ελέγξω τα τιμολόγια" \
  --date 2026-08-19
python3 scripts/command_center.py reminder-complete --id "x-apple-reminder://..."
python3 scripts/command_center.py reminder-update \
  --id "x-apple-reminder://..." \
  --title "Να ελέγξω τα τιμολόγια" \
  --date 2026-08-20
python3 scripts/command_center.py scratchpad-get
python3 scripts/command_center.py scratchpad-set --content "Σημείωση"
python3 scripts/command_center.py scratchpad-clear
python3 scripts/command_center.py sync-status
python3 scripts/command_center.py audit-list --limit 100
python3 scripts/command_center.py snapshot-list
python3 scripts/command_center.py snapshot-get --date 2026-08-18
python3 scripts/command_center.py mail
python3 scripts/command_center.py mail --query "invoice"
python3 scripts/command_center.py mail \
  --account "liakos.koulaxis@yahoo.com"

# Generate a local briefing immediately
python3 scripts/briefing_scheduler.py morning
python3 scripts/briefing_scheduler.py weekly

# Install macOS LaunchAgents: daily 08:30 and Monday 08:30
python3 scripts/install_briefing_schedule.py

# Install and open the localhost-only web dashboard
python3 scripts/install_web_dashboard.py

# After Supabase/GitHub OAuth setup
python3 scripts/configure_cloud_sync.py \
  --url "https://PROJECT.supabase.co" \
  --user-id "SUPABASE_AUTH_USER_UUID"
python3 scripts/install_cloud_sync.py
```

`dashboard` surfaces integration failures in its `errors` object. Report them;
never present a partial result as fully successful.

Scheduled briefings are stored privately under
`~/Library/Application Support/Command Center/Briefings/`, not in the Obsidian
vault. The morning briefing includes urgent items, calls, calendar entries,
Reminders, and mirrored todos for today.
Nested Work tasks include their parent path in JSON output and briefing previews.
The native Briefing Window opens automatically after a scheduled briefing is
generated; the notification remains available as a reminder.
The installer also registers a one-minute local watcher that sends one
notification 15 minutes before every timed Calendar event. It includes the local
Greek time and a Google Meet URL when Calendar exposes one in the event URL or
description.

The local dashboard listens only on `http://127.0.0.1:4317`. Its LaunchAgent
starts it at login and keeps it running. Browser code receives data through
independent CLI-backed endpoints and never reads or edits the vault directly.
Writes for tasks, reminders, Learning, captures, and Calendar events route through
the CLI so Markdown and macOS integrations remain synchronized.
Pending Learning items and metadata-only messages received in the last 48 hours
by `liakos.koulaxis@yahoo.com` load in independent panels.
Learning is grouped into Books, Articles, and Videos. Dashboard removal calls
`learning-complete`, preserving history rather than deleting the item.
Mail cards open the exact local message in Apple Mail. Agenda Join actions support
Google Meet, Microsoft Teams, and Zoom URLs exposed by Calendar.
The Reminders panel reads and mutates only the `Reminders` list. Completing a
task-synced reminder routes through task completion; standalone reminders are
completed directly in macOS Reminders.

`cloud/` contains the Vercel web app and Supabase schemas. The owner-only Mac
agent publishes the approved snapshot every 60 seconds and executes allowlisted
Personal/Work task, Reminder, Learning, and Calendar commands. It never uploads
Mail bodies, complete Work notes, local paths, or credentials.

`daily-rollover` creates:

- `Command Center/Daily Tasks/<N. Month YYYY>/<YYYY-MM-DD>.md`
- `Work/Daily Notes/<N. Month YYYY>/<YYYY-MM-DD>.md`

It carries forward only incomplete, deduplicated checkbox lines from the previous
date and never overwrites an existing daily file.

## Task mutations

Titles passed to the CLI must already be normalized to concise Greek.

```bash
python3 scripts/command_center.py task-add \
  --title "Να κατεβάσω τα τιμολόγια της Meta" \
  --area Personal \
  --date 2026-08-19

python3 scripts/command_center.py task-add \
  --title "Να διορθώσω το checkout" \
  --project BookIt

python3 scripts/command_center.py task-complete \
  --query "τιμολόγια της Meta"

python3 scripts/command_center.py task-reschedule \
  --query "checkout" \
  --date 2026-08-21

python3 scripts/command_center.py task-update \
  --query "checkout" \
  --current-date 2026-08-21 \
  --title "Να ελέγξω το checkout" \
  --date 2026-08-22
```

Use either `--project` or `--area`, not both. Valid areas are `Personal` and
`Work`. Without either, the task goes to `Inbox`.

## Projects

```bash
python3 scripts/command_center.py project-list
python3 scripts/command_center.py project-status --name BookIt
python3 scripts/command_center.py project-health --name BookIt
python3 scripts/command_center.py bookit-business
python3 scripts/command_center.py project-records --name BookIt
python3 scripts/command_center.py project-records --name BookIt --kind requirement

python3 scripts/command_center.py project-add \
  --name "New Project" \
  --path "$HOME/personal/new-project" \
  --area personal \
  --lifecycle development \
  --source-path "Personal/PProjects/New Project.md" \
  --health-check "API readiness|https://api.example.com/ready" \
  --render-service-id srv-example \
  --resend-domain example.com

python3 scripts/command_center.py project-add \
  --name "Remote Project" \
  --github owner/repository \
  --area work
```

With `--path`, the CLI discovers the GitHub origin and service names in
`render.yaml` or `render.yml`. It never reads environment values.

## Inbox and learning

```bash
python3 scripts/command_center.py capture \
  --text "Να εξετάσω την ιδέα για offline mode" \
  --project BookIt

python3 scripts/command_center.py inbox-list

python3 scripts/command_center.py waiting-add \
  --person "Alex" \
  --item "Να στείλει το production access" \
  --due 2026-08-21
python3 scripts/command_center.py waiting-list
python3 scripts/command_center.py waiting-complete --query "production access"

python3 scripts/command_center.py learning-add \
  --kind article \
  --title "Deep modules" \
  --url "https://example.com/deep-modules" \
  --project BookIt \
  --source "Χρήστης (chat)"

python3 scripts/command_center.py learning-list
python3 scripts/command_center.py learning-list --kind video --project BookIt
python3 scripts/command_center.py learning-complete --query "Deep modules"
```

## Work

```bash
python3 scripts/command_center.py work-briefing
python3 scripts/command_center.py work-sources
python3 scripts/command_center.py work-search --query "MCP"
python3 scripts/command_center.py work-read \
  --path "Work/1-1/2026-07-14.md"

python3 scripts/command_center.py work-task-add \
  --title "Να ελέγξω το PR" \
  --date 2026-08-19

python3 scripts/command_center.py work-task-complete \
  --query "ελέγξω το PR" \
  --date 2026-08-19
python3 scripts/command_center.py work-task-reschedule \
  --query "ελέγξω το PR" \
  --date 2026-08-20
python3 scripts/command_center.py work-task-update \
  --query "ελέγξω το PR" \
  --current-date 2026-08-20 \
  --title "Να ολοκληρώσω το PR review" \
  --date 2026-08-21

python3 scripts/command_center.py work-append \
  --kind brag \
  --text "Μείωσα τον χρόνο build κατά 20%."

python3 scripts/command_center.py work-append \
  --kind one_on_one \
  --date 2026-08-25 \
  --text "Να συζητήσουμε τις επόμενες προτεραιότητες."
```

`brag`, `connects`, and `one_on_one` writes require explicit user confirmation
of the exact text and path before execution.

## Live operations

```bash
python3 scripts/command_center.py project-health
python3 scripts/command_center.py project-health --name Fitcoach
python3 scripts/command_center.py project-health-set \
  --name BookIt \
  --health-check "Frontend|https://bookit.fyi" \
  --health-check "API health|https://api.bookit.fyi/healthz" \
  --source "Χρήστης (chat) · backend/src/main.rs"
python3 scripts/command_center.py bookit-business
python3 scripts/command_center.py render-logs --name BookIt --limit 30
python3 scripts/command_center.py render-logs \
  --name BookIt --level error --text "database"
python3 scripts/command_center.py resend-emails --name BookIt
```

`bookit-business` resolves `BOOKIT_ADMIN_TOKEN` from the environment, then from
macOS Keychain service `command-center-bookit-admin`. Responses are never stored.
`resend-emails` does the same with `RESEND_API_KEY` and Keychain service
`command-center-resend-api`; it shows five recent subjects with masked recipient
addresses and delivery status. Render uses the already-authenticated local
Render CLI. Logs are redacted and never persisted.

Append project knowledge with an explicit type and source:

```bash
python3 scripts/command_center.py project-record \
  --name BookIt \
  --kind requirement \
  --text "Οι ακυρώσεις πρέπει να εμφανίζονται στο ιστορικό." \
  --source "Χρήστης (chat)"

python3 scripts/command_center.py project-record \
  --name BookIt \
  --kind fact \
  --text "Το API επιστρέφει 429 μετά το όριο αιτημάτων." \
  --source "https://example.com/api-limits"
```

Valid kinds are `requirement`, `fact`, `idea`, `decision`, and `note`. To correct
history, append a replacement with `--supersedes <record-id>`; never rewrite the
old record.

Update the readable current summary while preserving an audit record:

```bash
python3 scripts/command_center.py project-summary-set \
  --name BookIt \
  --text "Πλατφόρμα online κρατήσεων για ελληνικές επιχειρήσεις." \
  --source "Χρήστης (chat)"
```

## Calendar writes

List calendars before asking the user to choose:

```bash
python3 scripts/command_center.py calendar-list
```

After the user confirms the exact calendar, title, local start time, and
duration:

```bash
python3 scripts/command_center.py calendar-add \
  --calendar Work \
  --title "Συνάντηση για το BookIt" \
  --start 2026-08-19T14:30 \
  --duration 45
```

Do not call `calendar-add` speculatively.

## Test/alternate vault

All filesystem commands accept a global vault override before the command:

```bash
python3 scripts/command_center.py --vault /tmp/test-vault task-list --view all
```
