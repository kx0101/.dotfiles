---
name: proactive-capture
description: Detect uncaptured follow-ups in any Copilot session. Use whenever the conversation reveals a concrete future task, reminder, calendar event, waiting-on item, learning resource, or durable project fact that may belong in Command Center, even when the user did not ask to capture it.
---

# Proactive capture

Surface a capture candidate after the user's main request is complete. An
explicit request to create or record something is already confirmed; route it
straight to `command-center` instead of asking twice.

## Qualify

Propose only an item that remains useful after this session:

- **Task** — a concrete action the user intends to perform later.
- **Reminder** — a dated nudge without a scheduled meeting.
- **Calendar event** — a commitment with a specific time.
- **Waiting-on** — another person owes a concrete action.
- **Learning** — a named book, article, or video saved for later.
- **Project note** — a durable requirement, decision, learned fact, or idea.

Current-session work, Copilot's own implementation steps, completed actions,
speculation, transient debugging notes, and existing Command Center items are
not candidates. Never propose storing credentials, secrets, Mail bodies, or
HR-sensitive content.

## Propose

Normalize the candidate into one concise item and choose its Command Center
type. Use `ask_user` to show the exact title, type, and known date/project, then
ask whether to record it. Ask once; a rejection suppresses the same candidate
for the rest of the session.

Group multiple candidates only when one confirmation can approve the exact
batch without ambiguity. Missing fields that change the destination or behavior
stay unresolved until the user answers.

## Record

After explicit approval, invoke `command-center` and use its interface to check
for a duplicate and perform the mutation. Calendar events still require exact
calendar, start time, and duration. Report the normalized item and resulting
date/status in one line. Approval is the completion criterion; no approval means
no write.
