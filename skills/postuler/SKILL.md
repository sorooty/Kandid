---
name: postuler
description: Prepare a complete application for one job offer (offer sheet, fit analysis, tailored CV and cover letter, honesty and ATS checks, review, status "Prêt"). Use when the user wants to apply to an offer given as a URL, pasted text or a Kandid offer number.
argument-hint: <url | texte de l'offre | numéro d'offre>
---

# Prepare an application

Kandid prepares, the user sends. Never submit a form, send a message or log into an account. Speak to the user in
their language (French unless the profile says otherwise). Read [rules.md](rules.md) before writing anything.

Offer: $ARGUMENTS

## Steps

1. **Locate things.** Run `kandid chemins` and keep the paths (profile, work, applications). If the profile file is
   missing, stop and tell the user to run the setup first.
2. **Get the offer.**
   - A number: `kandid offre voir <id>`; its `description` is the offer text.
   - A URL: read the page with WebFetch. If it fails or the text is clearly incomplete, ask the user to paste it.
     Never open a logged-in session.
   - Pasted text: use it as is.
   For a URL or text, save the text to a temporary file, then register it:
   `kandid offre ajouter --entreprise "<company>" --titre "<role>" [--url <url>] [--contrat <alternance|stage|cdi|cdd|interim|freelance>] [--lieu "<city>"] --texte <file> --json`.
   If it says the offer is already registered, use the number it gives.
   Create `<work>/<id>/` and write the offer text to `offre.md` there.
3. **Offer sheet and fit.** Follow [fit.md](fit.md): write `<work>/<id>/fiche.md`, then tell the user the fit in
   five lines at most. If the fit is weak or a hard requirement is missing, ask whether to go on (AskUserQuestion).
   Then `kandid offre statut <id> to_prepare` (skip if already further).
4. **CV spec.** Follow [documents.md](documents.md) to write `<work>/<id>/spec.yaml`, then
   `kandid validate <profile> <work>/<id>/spec.yaml` until it prints OK.
5. **Letter.** Follow [documents.md](documents.md) to write `<work>/<id>/letter.yaml`.
6. **Render.** `kandid name <profile> <spec> --doc CV --json` gives `folder` and `name`; do the same with
   `--doc LM`. Then:
   - `kandid render cv <profile> <spec> --out "<applications>/<folder>" --json`
   - `kandid render lm <profile> <spec> <letter> --out "<applications>/<folder LM>" --json`
   A blocked honesty check means the text claims something the profile does not hold: fix the spec or the letter,
   never the profile.
7. **Checks.**
   - `kandid ats <cv.pdf> --offer <work>/<id>/offre.md --company "<company>" --profile <profile> --json`, saved to
     `<work>/<id>/ats.json`. Missing keywords that the profile genuinely supports: pick wordings or skill groups that
     carry them and render again. Missing keywords the profile does not support stay missing.
   - `kandid wrapcheck <cv.pdf>`: shorten the wordings it flags and render again.
8. **Independent review.** Ask the `kandid:relecteur` agent to review the CV PDF, the letter PDF, `offre.md` and the
   profile. Fix every blocking point it reports, then render and check again.
9. **File and finish.**
   - `kandid offre document <id> <path>` for the CV PDF, the letter PDF and `fiche.md`.
   - `kandid offre statut <id> ready` (skip if already "ready").
   - Tell the user: the two PDF paths, the ATS score, the points to check, and that sending is up to them
     (`/kandid:formulaire <id>` can help fill an online form together).

Done when both PDFs exist, the honesty check passes, the reviewer has no blocking point and the status is "Prêt".
