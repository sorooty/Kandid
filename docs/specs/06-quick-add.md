# 06: Quick add of applications

- Status: To validate
- Related ADRs: 0003, 0007, 0008

## Problem

Entering an application by hand is the chore that makes people give up on tracking tools: too many fields, too many clicks, and it gets postponed. If adding is not almost instant, the tracking board becomes wrong and loses its point.

Goal: **an application added in under 10 seconds, in 3 actions at most.**

## User stories

- As a student, I add an application from any screen, with only two pieces of information.
- I paste what I have at hand (a link, a text, or just "Capgemini, alternance dev") and Kandid fills in the rest.
- I add several applications in a row without going back to an empty form.
- I bring into Kandid the spreadsheet I was already keeping.

## Scope

**In**
- **Quick add available everywhere**: a fixed button and the `N` keyboard shortcut, which open a compact panel without leaving the page.
- **Single smart field**:
  - a link or an offer text starts the import from spec 03;
  - a short text ("Company, position") is split into company and title, without calling the AI.
- **Only two required fields**: company and position. Everything else is optional and collapsible.
- **Smart defaults**: type taken from the onboarding, status "To apply" or "Sent" through an "I already applied" switch, today's date.
- **Chaining**: an "Add and continue" button that keeps the panel open and keeps the type and status.
- **Duplicate** an existing application for a similar offer.
- **Import of an existing spreadsheet** (`.csv`, which Excel and Google Sheets can save):
  - automatic detection of columns (company, position, status, date, link, notes);
  - manual correction of the mapping;
  - preview before import;
  - conversion of free-text statuses ("en attente", "refusé") to Kandid statuses.

**Out**
- `.xlsx` import (the student saves as CSV first).
- Import from other applications through their API.
- Adding by forwarding an email to Kandid (idea to study after the MVP).
- Sharing from the phone through the system share menu (needs the PWA, postponed by ADR 0008).

## Acceptance criteria

- [ ] An add with company and position takes 3 actions at most: open, type, confirm.
- [ ] The panel opens in less than 100 ms and the field is focused automatically.
- [ ] Splitting "Company, position" works without any network call to the AI.
- [ ] An import of 100 rows from a fictional reference spreadsheet completes without loss, with a report of skipped rows and the reason.
- [ ] Duplicates (same company and position, or same link) are flagged before confirming.
- [ ] The whole flow is usable with the keyboard and on a 375 px screen.

## Data

- Reuses `company`, `offer` (spec 03) and `application` (spec 05).
- `application.source`: `quick_add`, `offer_import`, `file_import`.

## Open questions

- Should we offer a spreadsheet template to download to make importing easier? Proposal: yes, the same format as the spec 05 export, so export and import are symmetric.
