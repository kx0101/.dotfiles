# Command Center on Vercel

The same responsive Command Center web UI, backed by an owner-only Supabase
snapshot and Mac command queue.

## Privacy model

The explicitly approved snapshot includes Personal/Work task metadata, Reminders,
Learning, Agenda, recent Mail metadata, system health, GitHub attention, masked
provider email activity, BookIt billing, calendars, and project operational
metadata. It never uploads Mail bodies, complete Work notes, local paths, or
credentials. RLS and the client gate allow only the configured GitHub user UUID.

## Supabase

1. Create a dedicated Supabase project.
2. Run these files in the SQL editor, in order:
   - [`supabase/schema.sql`](supabase/schema.sql)
   - [`supabase/health.sql`](supabase/health.sql)
   - [`supabase/mac-actions.sql`](supabase/mac-actions.sql)
   - [`supabase/owner-gate.sql`](supabase/owner-gate.sql)
   - [`supabase/scratchpad.sql`](supabase/scratchpad.sql)
   - [`supabase/reliability-actions.sql`](supabase/reliability-actions.sql)
   - [`supabase/daily-snapshots.sql`](supabase/daily-snapshots.sql)
   - [`supabase/command-locks.sql`](supabase/command-locks.sql)
3. Enable GitHub under Authentication → Providers.
4. Add the local and eventual Vercel URLs to Authentication → URL Configuration.
5. Copy `.env.example` to `.env.local` and set the project URL and anon key.

Run locally:

```bash
npm install
npm run dev
```

Deploy the `cloud/` directory to Vercel with:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

The anon key is intentionally browser-visible. Never place the service role key
in Vercel or this directory.

## Chat

The owner-only `/api/chat` function uses `gpt-4.1-nano` through the direct OpenAI
adapter. Add `OPENAI_API_KEY` as a sensitive Production environment variable in
Vercel; it never enters browser code or the repository. The function supports
Greek/Greeklish conversation, natural dates and times, multi-turn clarification,
and up to four typed create/update/complete/reopen/delete proposals for tasks,
Reminders, Calendar events, Learning, and project notes. Reminder proposals
preserve an optional local time as `YYYY-MM-DDTHH:mm`.

The browser sends each proposal to the existing Mac command queue only after the
owner presses Execute. A newer chat turn supersedes older unexecuted proposals.
Chat history stays in browser local storage. The last 8 messages plus only the
relevant approved calendar, project, task, Reminder, Agenda, Learning, and
project-note metadata are sent ephemerally to OpenAI and are not written to the
snapshot or vault.
Work data is limited to task title/date/status metadata; Work note content is
excluded.

## Mac sync agent

After the first GitHub login, copy the user's UUID from Supabase Authentication →
Users. Configure the Mac:

```bash
python3 ../scripts/configure_cloud_sync.py \
  --url "https://PROJECT.supabase.co" \
  --user-id "SUPABASE_AUTH_USER_UUID"

python3 ../scripts/install_cloud_sync.py
```

The configuration command prompts for the service role key and stores all sync
configuration in macOS Keychain. The LaunchAgent polls allowlisted commands and
publishes the approved snapshot every 60 seconds.

Apple Health setup is optional:

```bash
python3 ../scripts/configure_health_sync.py
```

This creates a restricted ingest token in Keychain and copies the iOS Shortcut
request template to the clipboard. The Shortcut itself remains a deferred
Personal task until completed.
