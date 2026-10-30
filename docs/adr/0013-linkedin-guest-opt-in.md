# 0013: LinkedIn guest source as a user opt-in

- Status: Accepted
- Date: 2026-10-30
- Amends: 0001

## Context

ADR 0001 rules out scraping. In practice, many work-study offers are only visible on LinkedIn, and the author's daily
watch already reads LinkedIn's public job pages without logging in. Leaving the source out pushes users to copy offers
by hand, or to write their own, less careful, script.

## Options

1. No LinkedIn source: strict reading of 0001, users paste offers manually.
2. A guest source, disabled by default, that the user turns on knowingly: public endpoints only, no login, no cookies,
   a pause between requests, a clear warning about LinkedIn's terms of use.

## Decision

Option 2. `sources/linkedin_guest.py` ships disabled. `/setup` and the settings page show the warning before it can be
enabled, and the choice is the user's responsibility.

## Consequences

- Default sources stay the public APIs (La bonne alternance, France Travail) and manual import.
- The source sends at most one request every 1.5 seconds, stops on a rate-limit answer and never retries in a loop.
- It reads offers only. Applying, messaging or any logged-in action stays out of scope (0001 unchanged on that point).
- If LinkedIn changes or blocks these endpoints, the source is dropped rather than worked around.
