# 0008: Restricted scope, me and my classmates

- Status: Superseded by 0011
- Date: 2026-10-27
- Supersedes in part: 0003, 0006, 0007

## Context

ADRs 0003 and 0006 prepare a consumer product (PWA, notifications, paid plans). Before that, we need a complete and reliable MVP for a small group: me and my classmates looking for a work-study contract, an internship or a student job. Aiming at the general public too early adds work without helping this first group.

## Options

1. Everyone installs Kandid on their own machine: local database, no account, their own API key. The simplest code, but installing it is out of reach for non-developers.
2. A single hosted instance, open by invitation: everyone signs in with a magic link and I pay for the AI for the whole group.

## Decision

Option 2, with these choices:

- **Audience**: twenty people at most. Sign-up is closed: only emails on an allowlist, managed server side, can sign in.
- **Hosting**: Vercel and Supabase (EU region) on their free tiers, ADR 0002 stack unchanged.
- **AI**: paid by me. ADR 0005 models (Haiku for extraction, Sonnet for writing). Quota of 10 letters per month and per person, as a server-side constant, plus a monthly spending cap in the Anthropic console.
- **Administration**: no admin interface. The allowlist, quotas and accounts are managed in Supabase Studio, costs in the Anthropic console and through a SQL view on `ai_run`.
- **Suspended**: the business model (ADR 0006), the PWA and notifications (ADR 0003).
- **Spec simplifications**: CSV export only, status change through a menu (no drag and drop), a single letter version kept.
- **Kept**: RLS on every table, zod validation, AI evaluations, no real data in the repository. Several people share the same database: each one must only see their own data.
- **Success criterion**: the one from ADR 0007 (10 students track at least 5 applications each).

## Consequences

- No public sign-up page and no subscription management to build.
- As the operator, I can see everyone's data in Supabase Studio: a short privacy notice at sign-in tells users, and I only look at it to fix a problem.
- Opening Kandid beyond the group will need a new ADR (sign-up, pricing, scaling, admin interface).
- Kandid may later become an agent framework (MCP server). To keep that door open, business logic and prompts stay in `packages/core` and `packages/ai`: the web app is just one client.
- ⚠️ Free tiers have limits (non-commercial use on Vercel, pausing of an inactive Supabase project): to check before going live.
- Cost tracking through `ai_run` stays useful to tune the quota and the cap.
