# Spec: `/setup` and scheduled tasks

## Problem

The plugin works, but only on a data folder prepared by hand: no `config.yaml`, no `profile.yaml`, no workspace
`CLAUDE.md`, and nothing runs unless the user types a command. A new user needs one guided command that turns their
existing CV and preferences into a working Kandid folder, and morning and evening tasks that prepare work without them.

## User story

As a student, I install the plugin and run `/kandid:setup`. It asks me a few choices with sensible defaults, reads my
existing CV and builds my profile section by section, asking me to confirm each one, then writes my settings, the
rules Claude follows in my folder, and a short "what to know" page. If I agree, it registers tasks that, at the
hours I chose, run the offer watch, list the follow-ups due and write an evening summary. Those tasks never send
anything.

## Scope

In:

- Skill `/kandid:setup` (user-invoked only). Questions through AskUserQuestion, each with a default, domain neutral:
  data folder (`~/.kandid`), applications folder, master CV folder or "start from the template", document languages,
  contract kinds and duration, school/work rhythm, area and radius, keywords, offer sources, task hours (8:30, 9:00,
  19:00, each can be turned off). Rerunning it on an existing folder edits the answers instead of starting over.
- `kandid importer <file>`: text of a `.tex`, `.pdf` (Poppler) or `.docx` (standard library, no new dependency) CV,
  as JSON sections. It only reads; the master folder stays untouched. The skill maps the text to `profile.yaml`,
  shows each section (identity, education, experiences, projects, skills) for validation, and never adds what the CV
  does not say. `kandid validate` checks the result. Without a CV, it starts from Camille's structure, emptied.
- `kandid setup ecrire <answers.json>`: deterministic writing, from validated answers, of `config.yaml`, the workspace
  `CLAUDE.md` and `A_SAVOIR.md` (from `tools/kandid_tools/templates/workspace/`), and the proposed `.claude/settings.json`, all in the data folder.
  Existing files are never overwritten silently: the command reports a diff and the skill asks first. Settings add
  the `deny` rule `Edit(//c/<master>/**)` (POSIX form, as the permission docs require on Windows; `Edit` rules also
  cover Write and shell redirections), so the master folder stays protected even when a hook cannot start. Reading
  it stays allowed. Settings are written only after an explicit yes.
- `kandid taches installer|lister|supprimer` and `kandid taches lancer <tache>`:
  - `installer` registers one Windows scheduled task per enabled task (`Register-ScheduledTask` through PowerShell,
    argument list built from fixed names and validated `HH:MM` times only, no user text), running
    `kandid taches lancer <tache>` at that hour.
  - `lancer` runs, from the data folder, `claude -p "/kandid:<skill>" --permission-mode dontAsk --allowedTools
    "Bash(kandid *)" --max-turns N --max-budget-usd X --output-format json --no-session-persistence`, records a `run`
    row (start, end, status, cost) and writes the report in `<data>/rapports/<date>-<tache>.md` and the raw output in
    `<data>/logs/`. `dontAsk` refuses anything not allowed, so a task cannot send, browse or write elsewhere.
  - Tasks: `veille` (8:30, `/kandid:veille`), `relances` (9:00, `/kandid:relance`, drafts only), `digest` (19:00, new
    skill `/kandid:digest`: new offers of the day, actions for tomorrow, from `kandid suivi` and the day's run).
  - cron and launchd equivalents documented in `A_SAVOIR.md`, not automated.
- `/setup` also warms the plugin's environment (`kandid chemins` once) so the first hook does not time out.
- `A_SAVOIR.md` template: commands, where files are, what tasks do and cost, how to turn them off, the rules.

Out: deadline reminders (need the calendar connector, phase 8), notifications in the UI (phase 7), email digest
(phase 8), Obsidian folder, migration of the real data (phase 10).

## Acceptance criteria

- `pnpm check` green; importer (three formats, fictional CVs), file writing (no silent overwrite, settings rules),
  task registration (argument list, time validation) and `lancer` (fake `claude` binary) unit tested.
- On an empty data folder, `/kandid:setup` with Camille's CV produces a valid `profile.yaml`, `config.yaml`,
  `CLAUDE.md`, `A_SAVOIR.md` and, after a yes, `.claude/settings.json`; `/kandid:postuler` then works from that folder.
- The three tasks show in the Task Scheduler; `kandid taches lancer veille` writes a report and a `run` row;
  `kandid taches supprimer` removes them.

## Data touched

Reads the CV the user points to (master folder, read-only). Writes in the data folder: profile, config, CLAUDE.md,
A_SAVOIR.md, settings, reports, logs, `run` rows. Task logs hold Claude's output, which may quote offers but no
secrets; CV content is never logged. Claude receives the CV text once, during import.

## Open questions

1. Scheduled tasks need a stable path to `kandid`, but the plugin folder changes with each update. Proposed: the task
   runs `uv run --project <plugin root>` and `/setup` (or a plugin update) re-registers tasks; alternative
   `uv tool install` of the CLI, which then needs its own updates.
2. Task budget: proposed default 0.50 USD and 30 turns per run, shown in `A_SAVOIR.md` and editable in `config.yaml`.
