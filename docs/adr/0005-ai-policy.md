# 0005: AI policy

- Status: Accepted, amended by 0011 (no direct model API calls in v2)
- Date: 2026-10-22

## Context

AI is the core of the value (tailored letters and CVs) and the only variable cost. Providers' free tiers have low quotas and sometimes use the data for training, which is incompatible with students' CVs, some of them from minors.

## Options

1. Free models in production: zero cost, GDPR and reliability risks.
2. Local models in development, cheap paid models in production with per-user quotas.

## Decision

Option 2:

- Development and tests: Ollama locally, fictional data only.
- Production: Claude API. Haiku 5.5 for extraction and classification, Sonnet 5.5 for final writing.
- Structured outputs, prompt caching, spending cap in the console.
- The "free tier" is a quota per user and per month (see ADR 0008).
- `packages/ai` exposes a provider-independent interface.

## Consequences

- Every call is recorded in `ai_run` (model, tokens, cost, duration).
- The model receives the minimum personal data; nothing sensitive in the logs.
- Prompts are versioned and covered by evaluations before any change.
