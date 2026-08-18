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
python3 scripts/command_center.py project-records --name BookIt
python3 scripts/command_center.py project-records --name BookIt --kind requirement

python3 scripts/command_center.py project-add \
  --name "New Project" \
  --path "$HOME/personal/new-project" \
  --area personal

python3 scripts/command_center.py project-add \
  --name "Remote Project" \
  --github owner/repository \
  --area work
```

With `--path`, the CLI discovers the GitHub origin and service names in
`render.yaml` or `render.yml`. It never reads environment values.

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
