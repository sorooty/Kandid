# 05: Application tracking

- Status: To validate
- Related ADRs: 0003, 0007, 0008

## Problem

Past ten applications, you lose track: who answered, who to follow up with, when the interview is. This is the screen the student will open every day.

## User stories

- As a student, I see all my applications grouped by stage.
- I move an application forward in one move and note what happened.
- I immediately know which applications need an action.
- I switch to a spreadsheet view to see everything at once, and I export my applications as CSV.

## Scope

**In**
- Column view by status on desktop, list grouped by status on mobile.
- Spreadsheet view: one row per application, sortable columns (company, position, type, status, sent date, last change, next action), choice of displayed columns, direct editing of status and next action in the cell.
- CSV export of the spreadsheet view (UTF-8 with BOM, Excel compatible), generated server side, respecting the active filters.
- Statuses and transitions defined in `packages/core`: To apply, Sent, Followed up, Interview, Offer, Rejected, No answer.
- Status change through a menu, on desktop and mobile (ADR 0008). A forbidden transition is refused with an explanation.
- Card: company, position, type, date of last change, next action.
- Detail sheet: offer, letter, dated notes, status history.
- "Next action" field with a date, highlighted when overdue.
- Manual creation of an application: see spec 06.
- Filter by type (work-study, internship, job) and search by company.
- Archiving of finished applications.

**Out**
- Drag and drop between columns, `.xlsx` export (ADR 0008).
- Email or push reminders (after the MVP).
- Statistics and indicators: see spec 07.
- Sharing the board with a school.
- Google Sheets sync.

## Acceptance criteria

- [ ] Transitions follow `canTransition` from `packages/core` exactly, in the interface and on the server.
- [ ] Every status change is recorded with its date in the history.
- [ ] The board stays smooth with 200 applications: paginated or virtualized list, INP under 200 ms.
- [ ] Everything is usable with the keyboard.
- [ ] The screen is usable on a 375 px wide phone.
- [ ] An export of 200 applications opens correctly in Excel and LibreOffice (accents, dates, columns).
- [ ] The export only contains the user's applications, filtered as on screen.

## Data

- `application`: `user_id`, `offer_id` (optional), `status`, `next_action`, `next_action_at`, `archived`, `updated_at`.
- `application_event`: `user_id`, `application_id`, `kind` (status, note), `from_status`, `to_status`, `note`, `created_at`.
- Indexes on (`user_id`, `status`) and (`user_id`, `next_action_at`).

## Open questions

- Do we need a "Draft" status before "To apply"? Proposal: no, "To apply" is enough.
