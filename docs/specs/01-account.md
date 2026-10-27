# 01: Account

- Status: Validated
- Related ADRs: 0002, 0004, 0007, 0008

## Problem

A student must be able to get into Kandid in a few seconds, without a password to remember, and keep full control over their data. Access is limited to invited people (ADR 0008).

## User stories

- As a student, I sign in with a link received by email.
- In under a minute, I fill in what I am looking for so Kandid adapts to me.
- I can download all my data or delete my account at any time.

## Scope

**In**
- Magic link sign-in (email) through Supabase Auth.
- Closed sign-up, enforced by Supabase Auth itself: public sign-ups are disabled and people are invited from Supabase Studio. The sign-in link is requested with `shouldCreateUser: false`. A server-side check alone would not be enough, since anyone can call the Auth API with the public key. An email that was not invited gets the same neutral message as an invited one.
- Short privacy notice on first sign-in: what is stored, who can see it (the operator, to fix problems), how to export or delete it.
- One-screen onboarding: first name, search type (work-study by default, internship, student job), school or program, desired start date, work-study rhythm (optional).
- "My account" page: edit this information, sign out, export data, delete account.
- Export: a JSON file with profile, offers, applications, letters and the original CV.
- Deletion: permanent removal of the database rows and stored files, after confirming by typing "SUPPRIMER".

**Out**
- Passwords, Google, LinkedIn or Apple sign-in.
- Public sign-up, school or multi-user accounts.

## Acceptance criteria

- [ ] An email that was not invited never receives a sign-in link and never gets an account (automated test).
- [ ] A new user lands on the onboarding right after their first sign-in, then on their tracking board.
- [ ] A user cannot read or modify any row belonging to another user (automated RLS test).
- [ ] The export contains all of the user's data and nothing else.
- [ ] After deletion, no row and no file linked to the user remains (automated test).
- [ ] Protected pages redirect to sign-in when the session has expired.

## Data

- `auth.users` (Supabase), filled only through invitations.
- `profile`: `user_id`, `first_name`, `search_type`, `school`, `start_date`, `work_study_rhythm`, `created_at`.

## Open questions

- Should we ask for the user's age? Useful for the apprenticeship age limit, but one more piece of data. Proposal: not in the MVP.
