# 07: Dashboard

- Status: To validate
- Related ADRs: 0003, 0007

## Problem

The tracking board shows each application, but not the overall situation or what to do today. A work-study search lasts months: the student needs to see progress to keep going.

## User stories

- As a student, when I open Kandid, I see at a glance where I stand.
- I know what I have to do today: follow up, prepare an interview, send an application.
- I set a goal of applications per week and see whether I am keeping it.

## Scope

**In**
- Home page after sign-in.
- **Indicators**: active applications, applications sent this week, response rate (answers received over applications sent), upcoming interviews.
- **To do**: next actions overdue or due today (spec 05), and follow-up suggestions for applications sent without an answer for 10 days.
- **Breakdown by status**: a simple horizontal bar, each segment links to the filtered board.
- Optional **weekly goal**: target number of applications, progress for the week.
- Polished empty state for a new user, with a call to quick add (spec 06).

**Out**
- Charts over time, statistics by source or by type (after the MVP).
- Comparison with other students.
- Notifications and reminder emails.

## Acceptance criteria

- [ ] All indicators come from a single aggregated server-side query, with no query per application.
- [ ] The page renders in less than 1 s with 200 applications (LCP under 2.5 s on mobile).
- [ ] Each indicator and each "To do" item leads to the matching filtered list.
- [ ] The 10-day delay for follow-up suggestions is a constant in `packages/core`, covered by tests.
- [ ] Status colors stay readable in light and dark mode, and are never the only way to tell statuses apart.

## Data

- Computed from `application` and `application_event` (spec 05), nothing extra stored.
- `profile.weekly_goal` (optional).

## Open questions

- Does the week start on Monday? Proposal: yes, French convention.
