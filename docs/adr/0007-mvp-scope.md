# 0007: MVP scope

- Status: Accepted, amended by 0008
- Date: 2026-10-22

## Context

Phase 0 is done. We need to ship a first useful version quickly, testable by real students, without spreading effort over phases 2 and 3.

## Options

1. Broad MVP: offer search, matching, extension and tracking. More appealing, but months before the first test.
2. MVP focused on one complete loop: profile, then offer, then tailored letter, then tracking. Quick to ship, each building block feeds the next.

## Decision

Option 2, with these choices:

- **Primary audience**: students looking for a work-study contract (alternance). Internships and student jobs are handled through the offer type.
- **Features**: account, profile from the CV, offer import, tailored letter with CV suggestions, application tracking with a spreadsheet view and export, quick add and import of an existing spreadsheet, simple dashboard (specs 01 to 07).
- **CV**: no full regeneration, only targeted suggestions per offer.
- **Payment**: none. A quota of 10 letter generations per month and per user, configurable server side.
- **Interface tone**: informal French ("tu").
- **Visual identity**: defined before the first screen.
- **Success criterion**: 10 student testers track at least 5 applications each in Kandid.

## Consequences

- Out of the MVP: offer connectors, browser extension, automatic follow-ups, match score, interview preparation, payment, offer sharing and community features.
- Out-of-scope ideas are written down in the vault (`Idées en vrac.md`) before possibly becoming a spec.
- The quota and the `ai_run` table give the real costs.
- Any feature outside this list needs a new ADR or waits for phase 2.
