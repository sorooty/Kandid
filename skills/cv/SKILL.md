---
name: cv
description: Regenerate the CV of an existing Kandid application, for instance after a profile change or a request to stress other experiences.
argument-hint: <numéro d'offre> [consigne]
---

# Regenerate a CV

Arguments: $ARGUMENTS (offer number, then an optional instruction).

1. `kandid chemins`, then read `<work>/<id>/spec.yaml`, `offre.md` and `fiche.md`. If there is no spec, the
   application was never prepared: suggest `/kandid:postuler <id>` and stop.
2. Apply the instruction by editing the spec, following
   [documents.md](${CLAUDE_PLUGIN_ROOT}/skills/postuler/documents.md) and
   [rules.md](${CLAUDE_PLUGIN_ROOT}/skills/postuler/rules.md). `kandid validate <profile> <spec>` until OK.
3. Render, check and review as in steps 6 to 8 of
   [the postuler skill](${CLAUDE_PLUGIN_ROOT}/skills/postuler/SKILL.md), CV only.
4. `kandid offre document <id> <cv.pdf>`. If the status was "Prêt" it stays so; tell the user what changed.
