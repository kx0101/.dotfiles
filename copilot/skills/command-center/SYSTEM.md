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
                    v
     cloud_sync.py (commands / snapshot / enrichment)
                    |
                    v
       Supabase snapshot + command queue
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
| Reminders/events | macOS Reminders/Calendar |
| Apple Health summary | Supabase `command_center_health_daily` |
| Audit timeline | `~/Library/Application Support/Command Center/audit.jsonl` |
| Daily history | Supabase `command_center_daily_snapshots` |

`daily-rollover` creates date/month files and applies the documented subtree
carry-over rule. Personal task add/complete/reschedule updates Tasks and daily
files. Dated Work mutations update the Daily Note. Tasks, Reminders, and
Calendar events are independent capture types.

Legacy `<!-- calendar: ... -->` blocks linked old mirrored tasks to providers.
`task-sync-detach` removes those provider items and metadata. New tasks contain no
provider metadata.

## Web app

- Vercel: <https://command-center-mobile-kappa.vercel.app>
- Markup: `cloud/index.html`
- Browser adapter: `cloud/src/main.js`
- Styling: `cloud/src/style.css`

The user-facing product name is **Πυξίδα**. Internal paths, CLI commands,
Supabase tables, and deployment identifiers retain the `command-center` name.

The Scratchpad autosaves after 800 ms, is owner-only, and persists until Clear.
It is not Inbox, project memory, or a Markdown note.

The Vercel chat posts to the owner-only `/api/chat` function. The function
validates the Supabase bearer token, owner UUID, request origin, message limits,
and action-specific payload before returning up to four typed proposals. It uses
`gpt-4.1-nano` directly through the OpenAI adapter; `OPENAI_API_KEY` exists only as
a sensitive Vercel Production environment variable. Only an explicit Execute
button submits each proposal to the existing command queue. The proposal
interface covers create/update/complete/reopen/delete for tasks, Reminders, and
Calendar events, plus Learning completion and project-note archival. A newer
chat turn supersedes earlier unexecuted proposals. Chat history remains in
browser local storage.

The first dashboard open per browser/day shows a dismissible briefing modal.
Closing it stores the date in browser local storage. The date navigator switches
to owner-only historical snapshots; past dates are read-only. Future dates use
the current 30-day Calendar plan, open Reminders, and existing Personal/Work
daily files, so scheduled events appear before that day's snapshot exists.
The header **Briefing** button opens the same modal on demand for the currently
selected day without changing the once-per-day automatic-open preference.
`scripts/briefing_contract.py` owns the daily briefing section and item shape.
The native scheduler renders that contract as Markdown; the Vercel modal renders
the same contract from the snapshot without deriving briefing rules in JavaScript.

Task and Reminder rows support title/date editing. Local writes call CLI update
commands directly; Vercel writes enter the allowlisted queue and use pending
overlays so refresh does not revert optimistic UI state.
Reminder dates may be date-only (`YYYY-MM-DD`) or timed local values
(`YYYY-MM-DDTHH:mm`). Timed values must survive the queue, macOS Reminders,
snapshots, display, and editing without being truncated.
The Reminders panel is scoped to the selected date; undated items appear only in
the current live view. Chat retains a separate capped catalog of all open
reminders for cross-date CRUD. User-facing dates use Greek 24-hour formatting;
ISO strings remain internal payload values.
New Calendar events default to the `Work` calendar in chat and the manual event
form unless the owner explicitly selects another calendar.

Todo capture may target an open parent by stable daily-file line number. No
selection creates a new root parent. Personal task storage remains flat in
`Tasks.md`; the daily file preserves the selected hierarchy and carries it
forward. Vercel project-note capture routes to append-only `project-record`.
Work children use the next direct numbered sibling (`1.`, `2.`, `3.`), matching
the established Obsidian list format. Capture uses a primary type dropdown and a
contextual subtype dropdown.
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
Three Mac jobs coordinate through one publication lock: commands every 10
seconds, core snapshots every 60 seconds, and slow provider enrichment every
10 minutes. Provider reads happen outside the lock; only command execution and
snapshot publication are serialized.

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

When the owner invokes chat, the last 8 chat messages and only relevant approved
calendar, project, task, Reminder, Agenda, Learning, and project-note metadata
are sent ephemerally to OpenAI for proposal resolution. Work exposure is limited
to task title/date/status metadata explicitly approved by the owner. They are
not added to the snapshot or vault. Complete Work notes, Mail bodies,
credentials, and provider payloads remain excluded.
The browser sends only messages and selected date. After bearer/owner
validation, the Vercel function loads the snapshot through Supabase RLS and
builds model context server-side.
Existing-item reads and mutations use the internal `search_entities` module.
The server infers type/date/time filters, searches snapshot metadata, and injects
at most 30 exact matches before the single model call. Casual and create-only
turns skip retrieval entirely. This deep module can gain OpenAI function-calling
or MCP adapters later without changing queue or proposal behavior.

Allowlisted cloud writes:

- add/complete Personal and Work tasks;
- add root or nested Personal/Work tasks;
- add/complete reminders;
- add/complete Learning;
- create Calendar events.
- update Calendar events through the queue adapter and `calendar-update`.
- update/reschedule Personal/Work tasks and Reminders.
- append project notes.

Pending/processing commands overlay the Vercel snapshot so a refresh does not
temporarily revert checked UI state.
Every active command also appears in the always-visible **Σε αναμονή** queue
near the top of Πυξίδα. Pending Calendar additions overlay the matching Agenda
date until the Mac publishes the resulting event or the command leaves the
active queue.
Every mutable row sends an `entity_key`. Supabase enforces one pending/processing
command per entity, and the UI disables that row until the command settles. This
prevents rapid checkbox clicks from queuing contradictory complete/reopen actions.
The semantic chat action `update-calendar-event` is adapted to the existing
allowlisted `add-calendar-event` queue action with `operation=update`; the Mac
agent routes it to `calendar-update`.

A successful Mac mutation remains `processing` with its result until the same
locked sync run publishes the new snapshot; only then does it become `done`.
Runs recover applied `processing` commands after a snapshot-publish failure.
The browser loads active commands before loading the snapshot. Together these
ordering invariants prevent a torn read where an overlay disappears while the
browser still holds the pre-mutation snapshot.
After enqueueing, the browser polls every 5 seconds only while active commands
exist and stops immediately when the queue settles.

Cloud captures remain durable while the Mac is offline. Vercel overlays pending
task, reminder, and Learning additions immediately so they remain visible until
the Mac executes them. `cloud_sync.py` uses a process lock; overlapping wake or
interval runs skip rather than publishing stale snapshots out of order.

Todo deletion is a soft delete: the provider item is removed, Markdown is marked
`→ διαγράφηκε`, the active dashboard hides it, and audit/history retain it.
Deleting a parent recursively soft-deletes all descendants before the parent.

Daily rollover merges missing incomplete lines into an existing target note as
well as creating new notes. A file created early by rescheduling must not block
the next day's carry-forward.
Carry-over inclusion is decided per root subtree: one unchecked node keeps the
whole non-deleted subtree and its exact checked/unchecked states. Only an
all-checked subtree is removed. Reconciliation applies the same rule to a
pre-existing target file.

The sync panel shows current snapshot time and pending/processing/failed counts.
Successful mutations append audit events with `cli` or `vercel` source labels.
The approved audit tail is included in each snapshot.

Provider enrichment is cached locally in
`~/Library/Application Support/Command Center/cloud-enrichment.json`. Command
completion and core snapshots reuse that cache instead of waiting for Mail,
GitHub, BookIt, Resend, or health reads.

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

- `com.command-center.briefing-morning` — daily 08:30;
- `com.command-center.briefing-weekly` — Monday 08:30;
- `com.command-center.call-reminders` — checks every minute, alerts 15 minutes
  before timed events;
- `com.command-center.cloud-sync` — command processing every 10 seconds;
- `com.command-center.cloud-snapshot` — core snapshot every 60 seconds;
- `com.command-center.cloud-enrichment` — provider enrichment every 10 minutes.

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
3. Add cloud actions only through the SQL allowlist and `command_arguments`.
4. Decide explicitly whether new data is local-only or snapshot-approved.
5. Verify local mutation, macOS sync, command queue, refreshed snapshot, owner
   RLS, and mobile wrapping.

## Current deferred item

The Personal task `Να ολοκληρώσω το Apple Health Shortcut για το Command Center`
tracks the unfinished iPhone Shortcut. The Health table, restricted RPC, token,
local/Vercel panels, and configuration script are ready.
