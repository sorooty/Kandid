# 03: Offer import

- Status: To validate
- Related ADRs: 0001, 0005, 0007

## Problem

Offers are scattered across dozens of sites. The student must be able to bring any of them into Kandid in one move, whatever the source.

## User stories

- As a student, I paste the link of an offer and Kandid extracts the essentials.
- If the link does not work, I paste the text of the offer instead.
- The imported offer becomes a "To apply" application in my tracking board.

## Scope

**In**
- A single field accepting a URL or raw text.
- For a URL: the page is fetched server side, only at the user's request, then its main text is extracted.
- Extraction by Claude Haiku: title, company, type (work-study, internship, job), location, remote work, start date, duration, rhythm, salary if stated, required skills, contact, deadline.
- Editable offer sheet before saving.
- Automatic creation of a "To apply" application (spec 05).
- Duplicate detection: same URL already imported by the user.

**Out**
- Offer search, alerts, bulk import (phase 2).
- Getting around a sign-in page or a CAPTCHA: in that case we offer copy-paste.

## Acceptance criteria

- [ ] On 10 reference offers (various sites), the key fields (title, company, type, location) are correct in at least 90% of cases.
- [ ] URL fetching is protected against SSRF: http and https only, private and local addresses refused, 10 s timeout, 2 MB maximum size.
- [ ] A fetch failure falls back to copy-paste with a clear message.
- [ ] The full import takes less than 8 seconds in 90% of cases.

## Data

- `company`: `user_id`, `name`, `website`.
- `offer`: `user_id`, `company_id`, `source_url`, `raw_text`, `title`, `type`, `location`, `remote`, `start_date`, `duration`, `rhythm`, `salary`, `skills`, `deadline`, `created_at`.
- Unique index on (`user_id`, `source_url`).

## Open questions

- Do we keep the raw text of the offer? Proposal: yes, it is used to generate the letter even if the offer disappears online.
