# 0014: Plugin layout: skills as commands, CLI through uv, hooks in Python

- Status: Accepted
- Date: 2026-10-30

## Context

The repository root is the plugin root (ADR 0011). The plugin needs slash commands, an independent reviewer and
guardrails that hold whatever the prompt says. The logic already lives in the `kandid` Python CLI; the plugin must
reach it on Windows first, without asking the user to install anything beyond uv, and without shell strings built from
user input. The official plugin documentation (checked on 2026-10-30) namespaces every component under the plugin name
(`/kandid:postuler`), recommends `skills/` over `commands/` for new plugins, puts a plugin's `bin/` on the Bash tool's
PATH, and runs hooks either through a shell or in exec form (`command` plus `args`).

## Options

1. Commands in `commands/` calling skills: two files per command for the same result.
2. Skills only, each one a slash command: one file per command, supporting files next to it, invocation control
   (`disable-model-invocation` for actions the user must start).
3. Hooks as shell or PowerShell scripts: no Python start-up cost, but a second implementation of path handling and
   config reading, harder to test, and shell parsing of paths with spaces.
4. Hooks in Python (`python -m kandid_tools.hooks <name>` through `uv run` in exec form): one implementation, unit
   tested, no shell; costs about half a second per matched tool call.

## Decision

Options 2 and 4. Skills in `skills/<name>/SKILL.md` are the commands; they call `kandid`, which `bin/kandid` runs
from the plugin's own project with `uv run --frozen --no-dev`. Hooks run the `kandid_tools.hooks` module in exec form,
with matchers narrowed to the tools they guard.

## Consequences

- No install step: the first call creates the virtual environment in the plugin folder (seconds with uv's cache), and
  again after each plugin update. `/setup` may later offer `uv tool install` instead.
- uv is a prerequisite, checked by `/setup`.
- Hooks add latency to Write, Edit and shell calls. Matchers stay narrow; a slow hook is a bug to fix, not a reason to
  drop a guardrail.
- Hooks run Python in isolated mode (`python -I`): otherwise the session's folder comes first on the import path and
  a planted `kandid_tools/hooks.py` would replace the guardrail (found in the security review).
- A hook that cannot decide asks the user. A hook that cannot start (uv missing, first environment build over the
  timeout) is a non-blocking error for Claude Code, so the call goes through: hooks are one layer, not the only one.
  The CLI repeats the master folder check, and `/setup` warms the environment and writes permission `deny` rules.
- `check-document` sees only `.tex` files written with Write or Edit; documents produced by `kandid render` are checked
  by the render itself.
