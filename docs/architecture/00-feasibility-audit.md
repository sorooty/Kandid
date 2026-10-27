# Kandid: audit and architectural feasibility study

> Status: **Accepted**, decisions formalized in `docs/adr/0001` to `0006`
> Date: 2026-10-22
> Scope: technical choices, risks, development organization

---

## 1. Current state (audit)

| Item | Finding |
|---|---|
| Code | Empty `code/` folder, no git repository |
| Documentation | `Kandid_OBS/` and `other/` empty (outside the code scope, not modified) |
| Dev machine | Windows 11, Node 24, npm 11, pnpm 12, Python 3.14, Docker 29, Git 2.55 |
| Team | 1 developer + Claude Code (desktop, then CLI in VS Code) |

**Conclusion**: greenfield project, no debt, complete tooling. Every option is open; the main criterion is therefore **the velocity of a solo developer assisted by AI**, without closing doors for later.

---

## 2. What Kandid must do (needs and technical constraints)

| Area | Feature | Resulting technical constraint |
|---|---|---|
| Profile | CV import (PDF/DOCX) into a structured profile (education, experience, skills, availability, work-study rhythm) | Document extraction + LLM, file storage, personal data |
| Offers | Aggregation of internship / work-study / student job offers; import of an offer by URL or copy-paste | API connectors, scheduled jobs, deduplication |
| Matching | Relevance score between offer and profile, with an explanation | Semantic search (vectors) + business rules |
| Writing | Tailored CV and cover letter per offer, customizable tone | LLM, PDF generation, document versioning |
| Tracking | Application board (kanban), statuses, follow-ups, interview reminders | Real-time CRUD, notifications, scheduled jobs |
| Preparation | Interview simulation, typical questions per company | Conversational LLM |
| Personalization | Themes, preferences, weekly goals | Design tokens, user preferences |

### Business specifics to model from the start
- **Work-study (alternance)**: apprenticeship vs professionalization contract, school/company rhythm, start date, school/CFA, age limit.
- **Internship**: mandatory agreement, duration, period, stipend beyond 2 months.
- **Student job**: weekly hours compatible with the timetable, one-off vs recurring.

These three types are not modeled the same way: plan a common `offer` model + a block of type-specific attributes.

---

## 3. The critical feasibility point: "automating applications"

This is the real risk of the project, more than the technology.

| Approach | Feasibility | Risk | Verdict |
|---|---|---|---|
| Scraping LinkedIn / Indeed / WTTJ | Technically possible | **Terms of service violation**, blocking, litigation (LinkedIn actively sues) | ❌ Rejected |
| 100% automatic application (a bot that applies alone) | Fragile (heterogeneous forms, CAPTCHA) | Terms of service, "spam" image with recruiters, harms the student | ❌ Rejected |
| **Official offer APIs** | Good | Low | ✅ Foundation |
| **Assisted manual import** (URL / copy-paste, then AI extraction) | Excellent, covers 100% of sites | Low (action started by the user) | ✅ Foundation |
| **Browser extension** that pre-fills forms on the page the user is viewing | Good | Low (the user validates and sends) | ✅ Phase 2 |

**Proposed guiding principle: "Kandid prepares, the student validates and sends."** Automation covers search, sorting, writing, tracking and follow-ups, not the final click.

### Legitimate offer sources (France)
- **France Travail, job offers API** (francetravail.io): free on registration, covers internships and work-study.
- **La bonne alternance** (api.apprentissage.beta.gouv.fr): public API dedicated to work-study, includes companies likely to hire (unsolicited applications).
- **Adzuna API**: aggregator with a free tier.
- **Public ATS job boards** (Greenhouse, Lever, Ashby, SmartRecruiters...): public endpoints per company, useful for target companies.

> Terms of use and quotas of each API to check during integration (one ADR per connector).

---

## 4. Compliance (GDPR), non-negotiable

- CV, contact details, background = **personal data**; some users may be minors (work-study from age 16).
- **EU** hosting (database, files, server functions).
- Subprocessors to list (host, LLM provider, emailing) with their DPAs.
- Account export and full deletion from the MVP (right of access / to erasure).
- Never send the LLM more than necessary; no sensitive data in the logs.
- Strict per-user data isolation at the database level (Row Level Security).

---

## 5. Recommended architecture

### 5.1 Overview

| Layer | Components | Role |
|---|---|---|
| Clients | `apps/web` (Next.js), `apps/extension` (WXT, phase 3) | Interface, Server Actions, API |
| Shared packages | `core`, `ai`, `db`, `ui` | Domain, prompts and evaluations, schema and migrations, design system |
| Services | Supabase EU (Postgres, pgvector, Auth, Storage, Cron, Queues), Claude API | Data, files, background jobs, writing and extraction |
| Sources | France Travail, La bonne alternance, Adzuna... | Job offers |

Clients call the shared packages, which alone talk to the services. Connectors feed the database through scheduled jobs.

### 5.2 Choices per layer

| Layer | Recommendation | Rejected alternatives | Why |
|---|---|---|---|
| Language | **TypeScript everywhere** | Python (FastAPI) back end | One language = one toolchain, types shared across front end, back end and extension. Python is only justified for heavy ML (not required). |
| Repository | **pnpm + Turborepo monorepo** | Multiple repositories | Web + extension + shared packages; Claude Code sees the whole context. |
| Front + back | **Next.js (App Router)**, Server Actions / Route Handlers | SPA + separate API, microservices | A single deployment, SSR, excellent Claude support. Microservices = unjustified overhead for a solo developer. |
| UI | **Tailwind CSS + shadcn/ui + design tokens** | MUI, Chakra | Components owned in the repository (customizable), themes through CSS variables, accessibility (Radix). |
| Database | **Postgres through Supabase (EU region)** + **pgvector** | Firebase, MongoDB | Relational model fits the domain (profile, offers, applications), RLS for isolation, vectors in the same database. Standard Postgres = reversible. |
| ORM / migrations | **Drizzle ORM** | Prisma | Lightweight, SQL-first, well typed, RLS compatible. |
| Auth | **Supabase Auth** (magic link + Google) | Auth.js, Clerk | Integrated with RLS, no extra cost. |
| Files | **Supabase Storage** (CVs, generated documents) | S3 | Same security perimeter as the database. |
| Background jobs | **Supabase Cron + Queues (pgmq)** at first | Inngest, Trigger.dev, Redis/BullMQ | No extra service; move to Inngest/Trigger.dev if workflows get complex. |
| AI | **Claude API**: Sonnet 5.5 for writing, Haiku 5.5 for extraction / classification; structured outputs, prompt caching | Other providers | Native PDF reading (CV import), writing quality in French. Light abstraction in `packages/ai` to stay in control. |
| Embeddings | Postgres full-text search in the MVP, then **Voyage AI** + pgvector | None | Do not over-architect matching before having real data. |
| PDF | **@react-pdf/renderer** | Puppeteer/Playwright | No headless browser in serverless; CV templates as React components. |
| Emails | **Resend** (React Email) | SendGrid | Simple, templates in React. |
| Hosting | **Vercel (functions in the Paris region)** + Supabase EU | Self-managed VPS | Zero ops at the start; free tiers are enough for the MVP. |
| Mobile | **PWA** (installable, notifications) | React Native / Expo | A single codebase; Expo possible later, reusing `core` and `ai`. |
| Extension (phase 2) | **WXT** | Plasmo | Modern, multi-browser, TypeScript. |
| Observability | Sentry + Vercel logs; AI cost/token tracking in the database | Datadog | Proportionate to the scope. |

### 5.3 Data model (first sketch)

```
user 1:1 profile 1:n education / experience / skill / availability
user 1:n document (source CV, generated CV, letter, versioned)
offer (source, external_id, type: internship|work-study|job, specific attributes, embedding)
user 1:n match (offer, score, explanation)
user 1:n application (offer, status, documents used, dates)
application 1:n event (follow-up, interview, answer, note)
company 1:n offer ; company 1:n contact
ai_run (type, model, tokens, cost, duration), for cost control
```

Status pipeline: to apply, sent, followed up, interview, then offer, rejected or no answer.

### 5.4 Monorepo structure

```
code/
  apps/
    web/              Next.js
    extension/        (phase 3)
  packages/
    core/             pure business logic (testable without database or network)
    ai/               versioned prompts, schemas, evaluations
    db/               Drizzle schema, migrations, RLS policies
    ui/               design system
  supabase/           local config, SQL migrations, seed
  docs/
    architecture/     this document
    adr/              architecture decisions (one per file)
    specs/            feature specifications
  .claude/
    settings.json     shared permissions and hooks
    agents/           project subagents
    commands/         project slash commands
  .github/workflows/  CI
  CLAUDE.md           project memory for Claude Code
```

---

## 6. Feasibility: summary

| Axis | Assessment | Comment |
|---|---|---|
| Technical | 🟢 High | Mature building blocks, no R&D needed. |
| Offer data | 🟡 Medium | Partial coverage through official APIs; compensated by manual import and the extension. |
| Legal | 🟡 Medium | Manageable if scraping and automatic sending are excluded, and if GDPR is handled from the MVP. |
| Costs | 🟢 Low at the start | Free hosting tiers; AI is the only variable cost, to measure (`ai_run`) and cap per user. |
| Solo workload | 🟡 Medium | Realistic if the MVP stays focused (see §7). |
| AI quality | 🟡 Medium | Requires evaluations (reference set of CVs and offers) to avoid generic letters or hallucinations. |

**Verdict: feasible**, provided that "automation" is refocused on assistance (§3).

---

## 7. Proposed phasing

| Phase | Content | Goal |
|---|---|---|
| **0. Foundations** | Monorepo, CI, local Supabase, auth, basic design system, CLAUDE.md, agents | A solid development base |
| **1. MVP** | CV import into profile; offer import by URL/text; letter + tailored CV generation; tracking board; account export/deletion | A complete loop useful to a student |
| **2. Search** | France Travail + La bonne alternance connectors; matching; alerts | Find offers for the student |
| **3. Active assistance** | Browser extension (pre-filling); follow-ups; interview preparation | Maximum time saved |
| **4. Growth** | Personal statistics, sharing with schools, mobile app if needed | Broaden usage |

---

## 8. Development practices (adapted to solo + Claude Code)

| "Enterprise" practice | Kandid adaptation |
|---|---|
| Specs before code | A short spec per feature (`docs/specs/`), Claude Code plan mode before implementation |
| ADR | Every structural decision in `docs/adr/NNNN-title.md` (context, options, decision, consequences) |
| Branches + PRs | Trunk-based: protected `main`, short `feat/...`, `fix/...` branches, PRs even when solo |
| Code review | `/code-review` before each merge + `/security-review` on auth, RLS, uploads; optionally the Claude GitHub action on PRs |
| Project subagents | `reviewer` (read-only), `test-writer`, `db-migration` (RLS, migrations), `ux-copy` (French copy) |
| Hooks | Automatic format + lint after edits; blocking reads of `.env` files |
| Tests | Vitest (core, ai), Playwright (critical flows), **AI evaluations** in `packages/ai` |
| CI | GitHub Actions: lint, typecheck, tests, build on every PR |
| Commits | Conventional Commits (`feat:`, `fix:`, `chore:`...) |
| Parallel work | Git worktrees (one Claude session per branch) for independent tasks |
| Secrets | `.env.local` never committed; variables on Vercel/Supabase |

---

## 9. Decisions to validate

1. **"Kandid prepares, the student sends" principle** (no scraping and no automatic sending).
2. **Stack**: TypeScript, Next.js, Supabase EU, Drizzle, Tailwind/shadcn, Claude API.
3. **Platform**: web + PWA first, extension in phase 2, native mobile later.
4. **Code hosting**: GitHub (private?).
5. **Business model** considered (free, freemium, schools), which affects how AI costs are capped.

Each validated point becomes an ADR in `docs/adr/`.
