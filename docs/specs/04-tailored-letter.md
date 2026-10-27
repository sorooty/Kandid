# 04: Tailored letter and CV suggestions

- Status: To validate
- Related ADRs: 0005, 0007, 0008

## Problem

Writing a different letter for each offer takes time, and a generic letter is spotted right away. The student needs a solid first version, faithful to their background, that they can adjust.

## User stories

- As a student, from an application I generate a letter that connects my background to the offer.
- I choose a tone and a length, edit the text, then copy it or export it as a PDF.
- I get a few concrete tips to adapt my CV to this offer.

## Scope

**In**
- Generation by Claude Sonnet from the profile (spec 02) and the offer (spec 03).
- Options: tone (sober or dynamic), length (short or standard).
- Text displayed progressively during generation (streaming).
- Simple text editor with autosave. Only the latest version is kept (ADR 0008).
- One-click copy and PDF export with the student's contact details.
- CV suggestions: 3 to 5 targeted tips (experience to highlight, missing keyword, skill to rephrase).
- Quota: 10 generations per month and per user, visible counter, clear message once reached.

**Out**
- Full CV regeneration, CV templates.
- Sending the letter from Kandid (ADR 0001).
- Translation into English.

## Acceptance criteria

- [ ] The letter mentions no degree, experience or skill absent from the profile (automated evaluation on a reference set).
- [ ] The letter names the company, the position and at least two specific elements of the offer.
- [ ] No character banned by CLAUDE.md in the generated text, and no hollow stock phrase.
- [ ] The first word appears in less than 3 seconds.
- [ ] The quota is checked server side before each generation.
- [ ] Every generation is recorded in `ai_run`.

## Data

- `letter`: `user_id`, `application_id`, `content`, `tone`, `length`, `created_at`, `updated_at`.
- `cv_suggestion`: `user_id`, `application_id`, `items` (JSON), `created_at`.
- Quota computed from `ai_run` over the current month.

## Open questions

- Does a manual edit count as a generation? Proposal: no, only AI generations count.
