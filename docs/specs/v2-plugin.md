# Spec: Claude Code plugin (v2 phase 4)

## Problem

The `kandid` CLI does the deterministic work (watch, rendering, ATS, honesty), but nothing yet tells Claude how to chain
it into an application, and nothing stops Claude from writing into the master CV folder or sending a message. Phase 4
turns the repository into a Claude Code plugin: slash commands that run the workflow, an independent reviewer, and
hooks that enforce the guardrails whatever the prompt says.

## User story

As a student, I type `/kandid:postuler <url or text>` and get, in my applications folder, an offer sheet, a CV and a
cover letter tailored from my profile only, an ATS report, and the application set to "Prêt". Every other step of my
search (watch, follow-ups, interview prep, weekly review) has its own command. Kandid never sends, submits or logs in
for me, and it cannot touch my master CV folder.

## Scope

In:

- `.claude-plugin/plugin.json` (name `kandid`, MIT, version) and `marketplace.json` so the repo installs as a
  marketplace of one plugin. Checked with `claude plugin validate`.
- Skills, one folder each under `skills/`, invoked as `/kandid:<name>` (the docs recommend skills over `commands/`; a
  skill is a slash command). Thin: they call `kandid` for anything deterministic and say when they are done.

  | Command | Role |
  |---|---|
  | `veille [source]` | run `kandid veille` (all enabled sources, or one), summarize the new offers, suggest which to prepare |
  | `postuler <url, texte ou id>` | offer sheet, job fit, spec, CV + letter, honesty, ATS, wrapcheck, filing, reviewer, status "Prêt" |
  | `cv <id>` / `lm <id>` | regenerate one document of an existing application |
  | `ats <pdf> [offre]` | ATS score alone |
  | `formulaire <id>` | fill an online form together in the browser; stops before submit, never handles accounts, files or sensitive fields, refuses cookies |
  | `suivi` | pipeline state and next actions |
  | `relance` | applications sent 7 or 14 days ago without answer, with draft follow-ups (never sent) |
  | `prep-entretien <id>` | company sheet, likely questions, questions to ask |
  | `comparer <ids>` | compare offers received |
  | `bilan` | weekly review: volume, answer rate, what works |
  | `aide` | commands and rules |

  `setup` and the master CV import come in phase 5. Prompts stay domain neutral: they read the profile and the offer,
  never assume a tech job.
- Agent `relecteur`: independent check before "Prêt" (every claim of the CV and letter traced to `profile.yaml`, offer
  requirements honestly addressed, tone, one page). Read-only tools plus `kandid` checks.
- CLI additions the skills need: `kandid offre voir <id>` (offer and history as JSON), `kandid offre statut <id>
  <statut>` (transition checked, event logged), `kandid offre document <id> <path>` (attach a generated file),
  `kandid suivi` (applications with days since last change and the next action), `kandid bilan [--jours]` (counts and
  rates), `kandid chemins` (every Kandid path as JSON). Config gains `paths.applications` (default
  `<data>/applications`) and `paths.master` (optional). Working files of an application (offer text, sheet, spec,
  letter, reports) go in `<data>/offres/<id>/`; CVs and letters in the applications folder, named by `kandid name`.
- Hooks in `hooks/hooks.json`, each run as `python -m kandid_tools.hooks <name>` (lighter than the full CLI), reading
  the hook JSON on stdin:
  - `protect-master` (PreToolUse on Write, Edit, MultiEdit, NotebookEdit): deny any write inside `paths.master`,
    whatever the spelling (long path prefix, loopback share, short name, junction). A Bash or PowerShell command
    naming that folder (native, Git Bash or home-relative form) or running inside it asks the user first; this shell
    check is best effort, so `kandid render` also refuses the master folder on its own.
  - `confirm-send` (PreToolUse on MCP tools whose action sends, replies, forwards, submits, shares, posts, publishes,
    invites, responds, comments, uploads or creates an event): asks the user, so nothing leaves without an explicit
    yes. Browser tools are not covered: `/kandid:formulaire` stopping before submit is a prompt rule.
  - `check-document` (PostToolUse on Write and Edit of a `.tex` file in the applications folder): runs the honesty
    check and feeds any unknown skill back to Claude. Documents rendered by `kandid render` are checked there instead.
  Hooks run `uv` in exec form (no shell string) and Python in isolated mode (`-I`), so a module in the session's folder
  cannot replace them. A hook that cannot decide (broken config, unexpected error) asks the user; without a configured
  master folder, `protect-master` has no opinion. A hook that cannot start (uv missing, timeout) lets the call through,
  as Claude Code treats it as a non-blocking error: `/setup` (phase 5) warms the environment and writes permission
  `deny` rules on the master folder as a second layer. `paths.*` must be absolute after `~` and variable expansion.
- `kandid offre document` only attaches files under the data or applications folder.
- `bin/kandid`: wrapper that runs the CLI from the plugin with `uv run`, so skills call plain `kandid` with no install
  step.
- Repository pre-commit (lefthook): refuse staged user data (databases, `profile.yaml`, `config.yaml`, letters and
  specs, PDF and Word files, logs, `.env*`, the data, applications and offers folders, any case) outside `examples/`
  and `tests/`, and email addresses or phone numbers outside those fixtures, reading the staged content.
- `templates/CLAUDE.md.tmpl` and `templates/settings.json.tmpl` (deny destructive commands), filled by `/setup` in
  phase 5.
- ADR 0014: plugin layout (skills as commands, CLI through `uv`, hooks as CLI subcommands).

Out: `/setup`, master CV import and scheduling (phase 5), API and UI (6 and 7), MCP connectors (8).

## Acceptance criteria

- `pnpm check` green; hooks and new CLI commands unit tested (hook JSON in, decision out).
- `claude plugin validate .` passes; `claude --plugin-dir .` lists the `/kandid:*` commands.
- In a test data folder with Camille's profile, `/kandid:postuler` on a fictional offer produces the offer sheet, CV and
  letter PDFs, ATS report and status "Prêt", and the reviewer's verdict.
- A Write into the configured master folder is denied; a send-like MCP tool asks first.

## Data touched

Reads `profile.yaml`, `config.yaml`, offers in `kandid.db`; writes generated documents in `paths.applications` and
statuses and events in `kandid.db`. Claude receives the profile and offer content needed for one application, nothing
else; secrets never reach a skill.

## Open questions

1. `bin/kandid` puts a virtual environment in the plugin folder, recreated when the plugin updates (seconds with uv's
   cache). Proposed: accept it; `/setup` can later offer `uv tool install` instead.
2. Some `postuler` steps need the offer page: proposed WebFetch on the URL the user gives, or pasted text when the site
   blocks it. Never a logged-in browser session.
