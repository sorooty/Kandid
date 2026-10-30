# 0011: Local-first Claude Code plugin and CRM

- Status: Accepted
- Date: 2026-10-30
- Supersedes: 0002, 0003, 0006, 0007, 0008, 0009, and 0010 (Drizzle and RLS, on the `legacy` branch only)
- Amends: 0005

## Context

Kandid v1 was a hosted Next.js and Supabase app for a small invited group. Meanwhile, the author's real job search ran
through Claude Code and a handful of local Python scripts (ATS check, CV and letter rendering from LaTeX), with rules
written in Markdown. That workflow produced the applications actually sent; the hosted app produced none yet. A hosted
service also means accounts, a database of other people's CVs, GDPR duties and an AI bill.

## Options

1. Keep the hosted app and add the scripts as server features: one product, but auth, hosting, RLS and API costs stay,
   and every user's CV goes through a server the author operates.
2. Rewrite as a local-first framework: a Claude Code plugin (skills, commands, hooks, agents) that drives Python tools,
   plus a local CRM web app over the same SQLite database. Each user runs it on their own machine with their own
   Claude Code subscription.

## Decision

Option 2. The repository root is the plugin root. Python tools (`tools/kandid_tools`, CLI `kandid`) hold the logic;
the CRM (`app/backend` FastAPI, `app/frontend` React) only reads, displays and triggers `claude -p` runs. User data
lives in a folder chosen at setup (default `%USERPROFILE%\.kandid\`), never in the repository.

## Consequences

- No accounts, no hosting, no RLS: the threat model becomes "do not leak the user's data into Git, logs or prompts".
- No direct model API calls and no Ollama: Claude Code does the language work under the user's own plan. ADR 0005
  still holds for its data rules (minimum personal data in prompts, never log CV content).
- What leaves the machine is what Claude Code sends to Anthropic (prompt content and files Claude reads). It is
  documented in `docs/A_SAVOIR.md`.
- Scheduled tasks consume the user's quota; they are documented and can be switched off.
- The v1 code stays available on the `legacy` branch and the `v1-legacy` tag.
