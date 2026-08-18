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
python3 scripts/command_center.py mail
python3 scripts/command_center.py mail --query "invoice"
```

`dashboard` surfaces integration failures in its `errors` object. Report them;
never present a partial result as fully successful.

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

python3 scripts/command_center.py work-task-complete --query "ελέγξω το PR"

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
python3 scripts/command_center.py bookit-business
python3 scripts/command_center.py render-logs --name BookIt --limit 30
python3 scripts/command_center.py render-logs \
  --name BookIt --level error --text "database"
python3 scripts/command_center.py resend-emails --name BookIt --limit 20
```

`bookit-business` resolves `BOOKIT_ADMIN_TOKEN` from the environment, then from
macOS Keychain service `command-center-bookit-admin`. Responses are never stored.
`resend-emails` does the same with `RESEND_API_KEY` and Keychain service
`command-center-resend-api`; recipient addresses and subjects are omitted.
Render uses the already-authenticated local Render CLI. Logs are redacted and
never persisted.

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
