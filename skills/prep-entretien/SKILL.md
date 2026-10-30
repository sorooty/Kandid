---
name: prep-entretien
description: Prepare a job interview for a Kandid application (company sheet, likely questions with answers drawn from the profile, questions to ask).
argument-hint: <numéro d'offre>
---

# Interview preparation

Offer: $ARGUMENTS. Speak to the user in their language.

1. `kandid offre voir <id>` and `kandid chemins`; read `fiche.md`, `spec.yaml` and `letter.yaml` in `<work>/<id>/`.
2. Company sheet: what the company does, size, recent news, the team's likely work. Search the web for public facts
   only, and send only the company's name and the role in searches, never profile content. Cite the sources.
3. Likely questions (about ten): motivation, the offer's main requirements, each experience in the CV, the gaps the
   fit analysis found. For each, an answer outline built only from the profile (situation, action, result), in the
   user's words, never invented.
4. Five questions the user can ask, specific to this company and role.
5. Write it all to `<work>/<id>/entretien.md`, then `kandid offre document <id> <that file>`.
