# Kandid

Claude Code framework for students looking for work-study (alternance), internships or jobs: a plugin (skills,
commands, hooks, agents) over a local SQLite database; the CRM is a Claude artifact over it (ADR 0016). Principle: Kandid prepares, the user validates and sends
(ADR 0001, 0013). Local-first, no hosted service (ADR 0011).

This file is for developing Kandid itself. The CLAUDE.md that users get is generated from
`tools/kandid_tools/templates/workspace/` by `/kandid:setup`.

## Stack
Python 3.11+ managed by uv (Ruff, pytest, typer, pydantic, Jinja2, SQLModel on SQLite, httpx, FastAPI),
pdflatex and Poppler for documents. Node 24 + pnpm only for tooling (Biome, lefthook, lint scripts). Claude Code
runs the language work (`claude -p` from the scheduled tasks). The React front is postponed (ADR 0016).

## Commands (repo root)
- `pnpm check`: lint (Biome, banned characters, Ruff) + tests (run before saying a task is done)
- `pnpm lint` / `pnpm format`: check / autofix
- `uv run pytest`, `uv run pytest tests/test_x.py -k name`
- `uv sync` after editing pyproject.toml

## Map
- `tools/kandid_tools`: Python package and `kandid` CLI. All business logic lives here, with tests in `tests/`.
- Plugin (ADR 0014): `.claude-plugin/` (manifest, marketplace), `skills/` (one per `/kandid:<name>` command),
  `agents/` (`relecteur`), `hooks/hooks.json` (runs `kandid_tools.hooks`), `bin/kandid` (CLI through uv),
  workspace templates in `tools/kandid_tools/templates/workspace/` (user CLAUDE.md and A_SAVOIR.md, filled by
  `/kandid:setup`). Try it with `claude --plugin-dir .`.
- `app/backend/kandid_api` (FastAPI, started by `kandid ui`): thin layer over `kandid_tools` and the SQLite
  database, kept for a later front (ADR 0016) and not advertised to users. `kandid_tools.bridge` runs `claude -p`
  for the scheduled tasks and the API (ADR 0015).
- `examples/`: fictional profile ("Camille Martin"), fictional offers
- `.claude/`: tooling for developing this repo (not shipped in the plugin)
- `docs/adr`: decisions; `docs/specs`: feature specs; `docs/INVENTAIRE.md`: what was kept from the legacy app and the scripts
- The former hosted app (Next.js, Supabase) lives on the `legacy` branch and tag `v1-legacy`.
- Read the relevant ADR/spec before working on a feature; don't load all docs.

## Code conventions
- No recursion on unbounded-depth data; use an explicit stack or iteration.
- Rule of three: extract shared logic on 3rd use (2nd if non-trivial). No abstraction unless it removes
  duplication or clearly improves readability.
- KISS. YAGNI: build only what is needed now. Exception: zero-cost future-proofing is fine.
- Search existing code (`tools/kandid_tools` first) before adding a function.
- No commented-out code, unused vars, dead code, TODO without issue link.
- Comments explain *why*, never paraphrase code.
- Names in English in code, French in UI.
- Skills and commands stay thin: they call the `kandid` CLI for anything deterministic.
- Paths with `pathlib`, never string concatenation; Windows is the primary target.

## Performance (measurable)
- Mind time/space complexity; no needless computation or allocation in hot paths.
- No N+1; index every FK and frequent filter; paginate lists; select needed columns only.

## Security and personal data
- User data (profile, CVs, letters, database, logs) lives in the data folder chosen at setup, never in the repository.
- Public repo: no real personal data anywhere, fictional fixtures only.
- The user's master CV folder is read-only for Kandid.
- Never submit a form, send a message or log into an account for the user; scheduled tasks only prepare.
- Never invent a skill or an experience: generated documents are checked against `profile.yaml`.
- Validate external input (API responses, offers, files) with pydantic. No shell string built from user input.
- No secrets in code; never read or print .env files.
- Send Claude the minimum personal data; never log CV content.
- Insecure option only if justified in code comment + PR description.

## Up-to-date knowledge
- Treat built-in knowledge as possibly outdated.
- Check installed version (pyproject.toml / uv.lock / package.json) before using a library API; consult official
  docs when unsure. Don't guess APIs, CLI flags or MCP server URLs.
- New dependency: versions released 2+ weeks ago (uv `exclude-newer`, pnpm `minimumReleaseAge`); never bypass it.
- Every external source actually consulted (doc, article, API page) gets a row in `../Kandid_OBS/Sources.md`:
  date, title, URL, what it was used for.
- Out-of-scope ideas from the user go to `../Kandid_OBS/Idées en vrac.md` (date, idea, value, hard points).
- These two vault files are the only ones Claude may edit outside `code/`.

## Writing
- Chat replies: concise, straight to the point. User speaks French: answer in French.
- Deliverables (docs, commits, PR, UI copy): correct grammar, natural human tone.
- Banned: filler ("Here is...", "In conclusion"), marketing superlatives, bullet lists for single ideas.
- Banned characters everywhere (files, commits, PR, chat): em dash and en dash, arrows of any kind, middle dot,
  ellipsis character, box-drawing characters. Use commas, colons, parentheses, "puis", "...", plain ASCII trees.
- Emojis only for status: ✅ done, 🚧 in progress, ⏳ planned, ❌ blocked, ⚠️ risk.
  Never decorative, never in code or UI unless deliberate design choice.
- English: code, docs (ADRs, specs, architecture), skills, prompts, agent and command definitions, CLAUDE.md.
- French: UI copy, commit descriptions, README (bilingual later).

## Workflow
- Non-trivial feature: spec in docs/specs, plan mode, branch, implement, `pnpm check`, review, PR.
- Branches: `feat/...`, `fix/...`, `chore/...` off `main`; short-lived. Never commit to `main` directly.
- Conventional Commits (enforced by lefthook), English type, French description, concise but explicit:
  `feat(tools): ajoute le score ATS en JSON`, `fix(veille): ignore les candidatures spontanées`.
- Commits and PRs are authored by the user only (GitHub: sorooty). Never add Co-Authored-By, "Generated with"
  or any Claude attribution, even for code Claude wrote.
- Before merge: `code-reviewer` agent or `/code-review`; `/security-review` on hooks, offer sources, the Claude
  bridge, file handling. `data-guardian` on anything touching user data.
- Structural decision: new ADR from docs/adr/0000-template.md.
- Commit/push only when asked.

## Environment
- Windows dev machine; LF line endings enforced by .gitattributes.
- Python via uv, Node 24 + pnpm, MiKTeX (pdflatex) and Poppler (pdftotext, pdfinfo) installed.
