# 0016: The CRM is a Claude artifact over the local database, the React app waits

- Status: Accepted
- Date: 2026-11-01

## Context

ADR 0011 planned a local CRM: a React page served by `kandid ui` over the FastAPI API (ADR 0015). Before building it,
the author tracked 31 real applications in a Claude artifact: a page published on claude.ai, with its own small
database, that Claude reads and writes during the conversation. It covered the daily need (table, statuses, next
actions, quick edits by asking Claude) with no front-end code to maintain, no server to start and no extra tokens
spent rebuilding screens. It also showed the risk: the artifact's database, the files on disk and a browser copy
disagreed within a day.

## Options

1. Build the React app now (phase 7): full control and offline, but weeks of front-end work before the mail and
   history features are used, and a second interface to keep in line with the skills.
2. Make the artifact's database the source of truth: no sync, but applications would live on claude.ai (against
   ADR 0011), and the watch, the review, the mail follow-up and the history import, which all work on SQLite, would
   have to be rewritten.
3. Keep SQLite as the only source of truth and use the artifact as a view: a skill pushes the applications from the
   CLI to the artifact, and any change goes through Claude and the `kandid` CLI before the view is refreshed.

## Decision

Option 3. The CRM is a Claude artifact that shows the applications held in the local SQLite database. The React app
is postponed, not cancelled: it stays a possible later interface over the same API.

## Consequences

- A sync skill reads `kandid suivi --json` and writes the artifact's records in one batch. The artifact holds a copy,
  never the reference: a field edited in the page is read back and applied through the CLI on the next sync, with the
  user's yes, before the view is overwritten.
- The copy is hosted on claude.ai under the user's account. Only the fields the table needs go there (company, title,
  status, dates, category, score, location, link, next action); no CV, letter, contact detail or note text.
- The artifact is created per user by `/kandid:setup` from a template in the plugin, so no personal URL or name is
  committed.
- The FastAPI API and the `claude -p` bridge stay: scheduled tasks use the bridge, and a future React app would use
  the API. Phase 7 is replaced by the artifact template and the sync skill.
