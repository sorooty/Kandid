# 02: Profile from the CV

- Status: To validate
- Related ADRs: 0005, 0007

## Problem

Retyping one's background is tedious. Yet the profile is the raw material of every tailored application: it must be complete and faithful.

## User stories

- As a student, I import my CV and find my background already filled in.
- I fix what the AI misunderstood, and my version is the one that counts.

## Scope

**In**
- Import of a PDF CV, 5 MB maximum, stored in a private bucket.
- Extraction by Claude Haiku as structured output: contact details, education, experience, skills, languages, links (portfolio, GitHub, LinkedIn).
- Result validated with zod before saving.
- Review screen: every section can be edited, added or removed.
- Manual profile creation without a CV.
- Re-importing a CV replaces the profile after confirmation.

**Out**
- DOCX, images, LinkedIn import.
- Smart merge between the old and the new profile.

## Acceptance criteria

- [ ] On a set of 5 fictional reference CVs, at least 90% of the fields are extracted correctly (evaluation in `packages/ai`).
- [ ] The extraction invents nothing that is not in the CV.
- [ ] An unreadable or oversized PDF shows a clear message and offers manual entry.
- [ ] CV content never appears in any log.
- [ ] Every extraction is recorded in `ai_run` (model, tokens, cost, duration).

## Data

- Storage: `cv/<user_id>/<file>.pdf`, access limited to the owner.
- `profile` (spec 01) completed by `education`, `experience`, `skill`, `language`, `link`, each with `user_id`.
- `ai_run`: `user_id`, `kind`, `model`, `input_tokens`, `output_tokens`, `cost`, `duration_ms`, `created_at`.

## Open questions

- Do we keep the original PDF after extraction? Proposal: yes, to be able to rerun the extraction; it is deleted with the account.
