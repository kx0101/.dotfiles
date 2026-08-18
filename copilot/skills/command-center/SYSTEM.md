# Command Center system

Read this before changing dashboard behavior, synchronization, scheduling,
notifications, cloud scope, or data ownership.

## Architecture

```text
Obsidian + macOS apps + provider CLIs/APIs
                    |
                    v
        command_center.py (only data interface)
                    |
        +-----------+-----------+
        |                       |
        v                       v
localhost:4317          Mac cloud_sync.py
local web app           every 60 seconds
                                |
                                v
                    Supabase owner-only snapshot
                    + allowlisted command queue
                                |
                                v
            command-center-mobile-kappa.vercel.app
```

The CLI owns validation, task routing, Markdown mutation, Calendar/Reminders
sync, provider access, and JSON contracts. Browser code never edits files or
invokes providers directly.

## Sources of truth

| Data | Source |
| --- | --- |
| Personal/project tasks | `Command Center/Tasks.md` |
| Personal daily view | `Command Center/Daily Tasks/<month>/<date>.md` |
| Work daily tasks | `Work/Daily Notes/<month>/<date>.md` |
| Project metadata/memory | `Command Center/Projects/*.md` |
| Learning | `Command Center/Learning.md` |
| Scratchpad | Supabase `command_center_scratchpad` |
| Reminders/events | macOS Reminders/Calendar, linked by stored IDs |
| Apple Health summary | Supabase `command_center_health_daily` |
| Audit timeline | `~/Library/Application Support/Command Center/audit.jsonl` |
| Daily history | Supabase `command_center_daily_snapshots` |

`daily-rollover` creates date/month files and carries only incomplete,
deduplicated items. Personal task add/complete/reschedule updates Tasks, daily
files, and Reminders. Dated Work mutations update the Daily Note and Work
Calendar.

Inline `<!-- calendar: ... -->` blocks are machine metadata linking a Markdown
todo to its exact Calendar/Reminder item. Obsidian hides them in Reading/Live
Preview. Keep them intact; Source mode shows them by design.

## Web apps

- Local: <http://127.0.0.1:4317>
- Vercel: <https://command-center-mobile-kappa.vercel.app>
- Shared CSS source: `cloud/src/style.css`
- Local markup/adapter: `web/index.html`, `web/app.js`
- Vercel markup/adapter: `cloud/index.html`, `cloud/src/main.js`

Both apps use the same panel order, DOM interface, workbench styling, responsive
breakpoints, capture patterns, task tree, project cards, and dialogs. Keep CSS
shared; do not create a second Vercel theme.

The Scratchpad autosaves after 800 ms, is owner-only, and persists until Clear.
It is not Inbox, project memory, or a Markdown note.

The first dashboard open per browser/day shows a dismissible briefing modal.
Closing it stores the date in browser local storage. The date navigator switches
to owner-only historical snapshots; past dates are read-only.

Task and Reminder rows support title/date editing. Local writes call CLI update
commands directly; Vercel writes enter the allowlisted queue and use pending
overlays so refresh does not revert optimistic UI state.

Todo capture may target an open parent by stable daily-file line number. No
selection creates a new root parent. Personal task storage remains flat in
`Tasks.md`; the daily file preserves the selected hierarchy and carries it
forward. Vercel project-note capture routes to append-only `project-record`.
Project modals display only `kind=note` records, not summaries or the full record
stream.
Deleting a project note appends an `archive` tombstone that supersedes the note;
physical project history remains intact.

Agenda rows are marked complete when a due-today Reminder is completed, a Work
Calendar todo title begins with `✓`, or a timed event has ended. Completed rows
remain visible with strikethrough.
Agenda deletion removes the Calendar/Reminder item. A linked task is closed as
`διαγράφηκε` in Markdown and retained in audit/history.

## Cloud synchronization

Supabase uses GitHub OAuth. Client and RLS are gated to the configured owner UUID.
The Mac agent publishes the approved snapshot and processes pending commands
every 60 seconds.

The snapshot currently contains:

- Personal and Work daily task metadata;
- Reminders and Calendar Agenda;
- Learning;
- recent Mail sender/subject/status/message ID metadata;
- project lifecycle/tasks and system liveness;
- GitHub attention;
- BookIt billing and masked Resend activity;
- writable calendar names.

It excludes Mail bodies, complete Work notes, local/source paths, raw provider
logs, and credentials.

Allowlisted cloud writes:

- add/complete Personal and Work tasks;
- add root or nested Personal/Work tasks;
- add/complete reminders;
- add/complete Learning;
- create Calendar events.
- update/reschedule Personal/Work tasks and Reminders.
- append project notes.

Pending/processing commands overlay the Vercel snapshot so a refresh does not
temporarily revert checked UI state.
Every mutable row sends an `entity_key`. Supabase enforces one pending/processing
command per entity, and the UI disables that row until the command settles. This
prevents rapid checkbox clicks from queuing contradictory complete/reopen actions.

Todo deletion is a soft delete: the provider item is removed, Markdown is marked
`→ διαγράφηκε`, the active dashboard hides it, and audit/history retain it.
Deleting a parent recursively soft-deletes all descendants before the parent.

Daily rollover merges missing incomplete lines into an existing target note as
well as creating new notes. A file created early by rescheduling must not block
the next day's carry-forward.

The sync panel shows current snapshot time and pending/processing/failed counts.
Successful mutations append audit events with `cli`, `local-web`, or `vercel`
source labels. The approved audit tail is included in each snapshot.

## Supabase setup

Run SQL files in order:

1. `cloud/supabase/schema.sql`
2. `cloud/supabase/health.sql`
3. `cloud/supabase/mac-actions.sql`
4. `cloud/supabase/owner-gate.sql`
5. `cloud/supabase/scratchpad.sql`
6. `cloud/supabase/reliability-actions.sql`
7. `cloud/supabase/daily-snapshots.sql`
8. `cloud/supabase/command-locks.sql`

Public browser configuration belongs in ignored `cloud/.env.local` and Vercel:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

Mac-only configuration belongs in Keychain:

- `command-center-supabase-url`
- `command-center-supabase-user`
- `command-center-supabase-service`
- `command-center-health-ingest-token`

The service-role key never enters Vercel, source files, prompts, or browser code.

## Background jobs

LaunchAgents:

- `com.command-center.dashboard` — optional localhost web server; currently
  disabled because Vercel is the primary interface;
- `com.command-center.briefing-morning` — daily 08:30;
- `com.command-center.briefing-weekly` — Monday 08:30;
- `com.command-center.call-reminders` — checks every minute, alerts 15 minutes
  before timed events;
- `com.command-center.cloud-sync` — Supabase command/snapshot sync every minute.

Logs live under `~/Library/Logs/CommandCenter/`. Briefing archives live under
`~/Library/Application Support/Command Center/Briefings/`.

## Privacy

External responses are ephemeral locally unless they are fields in the explicitly
approved owner-only cloud snapshot. Mail bodies and complete Work notes remain
local. Project health uses liveness endpoints; readiness endpoints may wake
databases and are reserved for orchestrator gates. Credentials stay in Keychain.

## Extension workflow

1. Put behavior behind a CLI command with JSON output.
2. Preserve the source of truth and all linked macOS IDs.
3. Add local web endpoints as thin CLI adapters.
4. Add cloud actions only through the SQL allowlist and `command_arguments`.
5. Decide explicitly whether new data is local-only or snapshot-approved.
6. Use the shared CSS and matching DOM structure.
7. Verify local mutation, macOS sync, command queue, refreshed snapshot, owner
   RLS, and mobile wrapping.

## Current deferred item

The Personal task `Να ολοκληρώσω το Apple Health Shortcut για το Command Center`
tracks the unfinished iPhone Shortcut. The Health table, restricted RPC, token,
local/Vercel panels, and configuration script are ready.
