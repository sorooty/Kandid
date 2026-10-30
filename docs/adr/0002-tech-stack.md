# 0002: Tech stack

- Status: Superseded by 0011
- Date: 2026-10-22

## Context

A single developer, assisted by Claude Code. The main criterion is velocity without closing doors: web, extension and maybe mobile will share the business logic. The data is personal (GDPR) and must stay in the EU.

## Options

1. TypeScript everywhere, monorepo, Next.js + Supabase.
2. TypeScript front end + Python back end (FastAPI): useful for heavy ML, but two toolchains to maintain.
3. Microservices: unjustified overhead at this scale.

## Decision

Option 1:

- pnpm + Turborepo monorepo
- Next.js (App Router), Server Components by default
- Supabase in the EU region: Postgres, pgvector, Auth, Storage, Cron, Queues
- Drizzle ORM, Row Level Security on every table
- Tailwind CSS + shadcn/ui, themes through design tokens
- Biome (lint + format), Vitest, Playwright
- Hosting on Vercel, functions in the Paris region

## Consequences

- Standard Postgres: leaving Supabase stays possible.
- Background jobs on pg_cron + pgmq at first; Inngest or Trigger.dev if workflows get complex (new ADR).
- No Python until an ML need requires it.
