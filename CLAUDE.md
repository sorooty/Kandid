# Kandid

Helps students find and apply to internships, work-study (alternance) and student jobs.
Principle: Kandid prepares, the student validates and sends (no scraping, no auto-submit). See docs/adr/0001.

## Stack
TypeScript, pnpm + Turborepo monorepo, Next.js 16 (App Router, React Compiler), Tailwind 4 + shadcn/ui,
Supabase EU (Postgres, pgvector, Auth, Storage, RLS), Drizzle, Claude API (Haiku extraction, Sonnet writing;
Ollama locally), Biome, Vitest, Playwright, Vercel.

## Commands (repo root)
- `pnpm dev`: run apps
- `pnpm check`: lint + typecheck + tests (run before saying a task is done)
- `pnpm lint` / `pnpm format`: Biome check / autofix
- `pnpm typecheck`, `pnpm test`, `pnpm build`
- Scope one package: `pnpm --filter @kandid/core test`

## Map
- `apps/web`: Next.js app (UI, Server Actions, route handlers)
- `packages/core`: pure domain logic, no framework/DB/network imports
- Planned, create only when first needed: `packages/ai` (prompts, schemas, evals), `packages/db` (Drizzle schema,
  migrations, RLS), `packages/ui` (design system), `apps/extension` (WXT, phase 3)
- `docs/adr`: architecture decisions; `docs/specs`: feature specs; `docs/architecture`: overview
- Read the relevant ADR/spec before working on a feature; don't load all docs.

## Code conventions
- No recursion on unbounded-depth data; use an explicit stack or iteration.
- Rule of three: extract shared logic on 3rd use (2nd if non-trivial). No abstraction unless it removes
  duplication or clearly improves readability.
- KISS. YAGNI: build only what is needed now. Exception: zero-cost future-proofing is fine.
- Search existing code (packages/core first) before adding a function.
- No commented-out code, unused vars, dead code, TODO without issue link.
- Comments explain *why*, never paraphrase code.
- Names in English in code, French in UI.
- Business rules live in packages/core with unit tests; apps stay thin.

## Performance (measurable)
- Mind time/space complexity; no needless computation or allocation in hot paths.
- Server Components by default; "use client" only for interactivity.
- No request waterfalls; parallelize or join. No N+1.
- Select needed columns only, paginate lists, index every FK and frequent filter.
- Lazy-load heavy deps; next/image for images.
- Budgets: LCP < 2.5s, INP < 200ms, client JS < 150KB per route.

## Security by default
- RLS enabled on every table, deny by default.
- Validate every server input with zod. Never trust client data.
- No secrets client-side; never read or print .env files.
- Public repo: no real personal data anywhere, fictional fixtures only.
- Send the LLM the minimum personal data; never log CV content.
- Insecure option only if justified in code comment + PR description.

## Up-to-date knowledge
- Treat built-in knowledge as possibly outdated.
- Check installed version (package.json / lockfile) before using a library API; consult official docs when unsure.
  Don't guess APIs.
- New dependency: prefer versions released 2+ weeks ago (pnpm minimumReleaseAge); never bypass it.
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
- English: code, docs (ADRs, specs, architecture), AI prompts, agent and command definitions, CLAUDE.md.
- French: UI copy, commit descriptions, README (bilingual later).

## Workflow
- Non-trivial feature: spec in docs/specs, plan mode, branch, implement, `pnpm check`, review, PR.
- Branches: `feat/...`, `fix/...`, `chore/...` off `main`; short-lived. Never commit to `main` directly.
- Conventional Commits (enforced by lefthook), English type, French description, concise but explicit:
  `feat(web): ajoute le tableau de suivi`, `fix(core): bloque le passage direct à entretien`.
- Commits and PRs are authored by the user only (GitHub: sorooty). Never add Co-Authored-By, "Generated with"
  or any Claude attribution, even for code Claude wrote.
- Before merge: `code-reviewer` agent or `/code-review`; `/security-review` on auth, RLS, uploads, AI input.
- Structural decision: new ADR from docs/adr/0000-template.md.
- Commit/push only when asked.

## Environment
- Windows dev machine; LF line endings enforced by .gitattributes.
- Docker available (local Supabase).
