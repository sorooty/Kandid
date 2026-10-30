---
name: lm
description: Rewrite the cover letter of an existing Kandid application (new angle, shorter, other language, user's remarks).
argument-hint: <numéro d'offre> [consigne]
---

# Rewrite a cover letter

Arguments: $ARGUMENTS (offer number, then an optional instruction).

1. `kandid chemins`, then read `<work>/<id>/letter.yaml`, `spec.yaml`, `offre.md` and `fiche.md`. Without a spec,
   suggest `/kandid:postuler <id>` and stop.
2. Rewrite `letter.yaml` with the instruction, following
   [documents.md](${CLAUDE_PLUGIN_ROOT}/skills/postuler/documents.md) and
   [rules.md](${CLAUDE_PLUGIN_ROOT}/skills/postuler/rules.md).
3. `kandid name <profile> <spec> --doc LM --json`, then
   `kandid render lm <profile> <spec> <letter> --out "<applications>/<folder>" --json`. A blocked honesty check
   means the letter claims something the profile does not hold: rewrite, never edit the profile.
4. Ask the `kandid:relecteur` agent to review the new letter; fix blocking points.
5. `kandid offre document <id> <letter.pdf>` and show the user the new letter text.
