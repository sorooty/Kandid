# 0006: Freemium business model

- Status: Superseded by 0011
- Date: 2026-10-22

## Context

The audience is students on a tight budget, and the search is seasonal (roughly February to September for work-study). We need to attract widely and convert without deceptive practices.

## Decision

- Free: unlimited application tracking, a few AI generations per month.
- Season pass: extended access for a limited period, aligned with the search season.
- Low-priced monthly student plan.
- Referrals rewarded with AI credits.
- In the medium term: licenses for schools and apprentice training centers (CFA).

## Consequences

- Quotas and entitlements are managed server side, never client side.
- No dark patterns: one-click cancellation, no fake countdown.
- AI costs per user (`ai_run`) are used to set prices and quotas.
