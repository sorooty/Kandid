# 0002 : Stack technique

- Statut : Accepté
- Date : 2026-10-22

## Contexte

Un développeur seul, assisté par Claude Code. Le critère dominant est la vélocité sans fermer de portes : web, extension et peut-être mobile partageront la logique métier. Les données sont personnelles (RGPD) et doivent rester dans l'UE.

## Options

1. TypeScript partout, monorepo, Next.js + Supabase.
2. Front TypeScript + backend Python (FastAPI) : utile pour du ML lourd, mais deux outillages à maintenir.
3. Microservices : surcoût injustifié à cette échelle.

## Décision

Option 1 :

- Monorepo pnpm + Turborepo
- Next.js (App Router), Server Components par défaut
- Supabase région UE : Postgres, pgvector, Auth, Storage, Cron, Queues
- Drizzle ORM, Row Level Security sur toutes les tables
- Tailwind CSS + shadcn/ui, thèmes par design tokens
- Biome (lint + format), Vitest, Playwright
- Hébergement Vercel, fonctions en région Paris

## Conséquences

- Postgres standard : la sortie de Supabase reste possible.
- Tâches de fond sur pg_cron + pgmq au départ ; Inngest ou Trigger.dev si les workflows se complexifient (nouvelle ADR).
- Pas de Python tant qu'aucun besoin ML ne l'impose.
