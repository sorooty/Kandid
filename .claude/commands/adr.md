---
description: Draft a new architecture decision record
argument-hint: <decision title>
---

Draft an ADR for "$ARGUMENTS":

1. Find the next number in docs/adr (highest existing + 1, four digits).
2. Copy the structure of docs/adr/0000-template.md into `docs/adr/NNNN-<kebab-title>.md`, in English, status "Proposed", today's date.
3. Fill Context, Options (at least two, with real trade-offs), Decision, Consequences. Keep it short: an ADR is read in two minutes.
4. If it replaces an older ADR, mark the old one "Superseded by NNNN".
5. Show me the draft; switch the status to "Accepted" only after I confirm.
