# 0010: Data access with Drizzle under RLS

- Status: Accepted
- Date: 2026-10-27

## Context

ADR 0002 picks Drizzle and RLS on every table. Drizzle connects straight to Postgres with a privileged role, so RLS does not apply to its queries by default. Supabase's own client (PostgREST) applies RLS, but makes joins and aggregated queries awkward, and spec 07 needs a single aggregated query for the dashboard.

## Options

1. supabase-js for every user query: RLS applies for free, but no typed SQL, joins through PostgREST syntax only, and two schema definitions to keep in sync.
2. Drizzle with a privileged role and `user_id` filters written by hand: simple, but one forgotten filter leaks another user's data, and RLS becomes decoration.
3. Drizzle inside a transaction that switches to the `authenticated` role and sets the user's JWT claims: RLS applies to every query, with typed SQL and joins.

## Decision

Option 3. `packages/db` exposes `withUser(claims, fn)`: it opens a transaction, sets `request.jwt.claims` and `role authenticated` locally, then runs `fn` with the Drizzle transaction. Every user-scoped query goes through it. Queries are still written with explicit `user_id` filters when they help the planner, but isolation never depends on them.

The privileged connection is only used for migrations and tests. Deleting an account goes through the Supabase admin API with the secret key, server side.

## Consequences

- One extra round trip per request (the `set_config` calls run in the same transaction).
- Connections go through the Supabase pooler in transaction mode, so prepared statements are disabled.
- RLS policies are declared in the Drizzle schema and generated into Supabase migrations, so policies and tables live in one place.
- An integration test with two users proves isolation on every new table.
