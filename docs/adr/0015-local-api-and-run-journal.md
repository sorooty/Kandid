# 0015: Local API guards and a run journal in SQLite

- Status: Accepted
- Date: 2026-10-30

## Context

The CRM (ADR 0011) is a web page served by a FastAPI process on the user's machine. That process can move
applications and start `claude -p` runs, which spend the user's quota and write in their data folder. Any website the
user visits can send requests to `127.0.0.1`, and a site whose domain is rebound to `127.0.0.1` can even read the
answers. The CRM also has to show runs live and keep them afterwards, while a run's raw stream carries everything
Claude read: profile, CV and letter text (ADR 0005).

## Options

1. A random token per launch, given to the page through the URL: strong, but every reload, bookmark and the `.bat`
   shortcut have to carry it.
2. No token; the server binds to `127.0.0.1` only, refuses any `Host` other than `127.0.0.1` or `localhost`, and
   accepts a state-changing request only with a JSON body and, when the browser sends one, a same-origin `Origin`.
3. For the journal: keep runs in memory and push them to the page, or store a reduced copy of each stream message in
   SQLite and let the page read from there.

## Decision

Option 2 for the API: a cross-site page cannot send JSON without a CORS preflight, which the API never answers, and
the `Host` check defeats DNS rebinding. Runs are journaled in SQLite (`clauderun`, `claudeevent`): each stream message
is reduced to its kind, Claude's text, the tool name and a one-line summary of its input (a `kandid` command, a path).
Tool outputs are never stored. The live view polls that table over SSE, so a reload or a second tab resumes from
`Last-Event-ID`, and scheduled tasks, which run in their own process, appear in the same journal. Runs only accept
fixed actions with at most an offer number, and one run at a time per process.

## Consequences

- A local program running as the user can still call the API; that is outside this threat model, since it could read
  the data folder directly anyway.
- Claude's own messages are stored and may quote the profile; they are what the user reads, and stay in their data
  folder. The raw stream stays in `<data>/logs/`, as for the scheduled tasks, minus the tool results
  (the `user` lines), which may hold CV or profile text.
- If the CRM ever listens on another interface or serves several users, this decision has to be revisited (token,
  authentication).
- The journal grows by a few dozen rows per run; a cleanup command can come when it matters.
