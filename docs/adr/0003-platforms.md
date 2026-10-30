# 0003: Target platforms

- Status: Superseded by 0011
- Date: 2026-10-22

## Context

Students search from their phone as much as from their computer. Maintaining several codebases is out of reach for a solo developer.

## Decision

1. Responsive web + PWA (installable, notifications) from the MVP.
2. Browser extension (WXT) in phase 3, for pre-filling forms.
3. Native app (Expo) only if the PWA shows its limits, reusing `packages/core` and `packages/ai`.

## Consequences

- Mobile-first interface from the first mockup.
- The business logic never depends on Next.js: it lives in `packages/core`.
