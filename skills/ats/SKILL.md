---
name: ats
description: Score a CV PDF for applicant tracking systems (format checks, and keywords found or missing against an offer if given).
argument-hint: <cv.pdf> [offre.txt ou numéro d'offre]
---

# ATS check

Arguments: $ARGUMENTS.

1. If the second argument is an offer number, get its text with `kandid offre voir <id>` and write the `description`
   to a temporary file. A file path is used as is.
2. `kandid ats <cv.pdf> [--offer <file>] [--company "<company>"] [--profile <profile from kandid chemins>] --json`.
3. Report the score, each format problem with its fix, and the missing keywords split in two: those the profile
   supports (worth adding through another wording or skill group) and those it does not (they stay out, say so).
