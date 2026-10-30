---
name: comparer
description: Compare several job offers the user received or is considering, on the criteria that matter to them.
argument-hint: <numéros d'offres>
---

# Compare offers

Offers: $ARGUMENTS.

1. `kandid offre voir <id>` for each, and `fiche.md` in its work folder when it exists.
2. Ask the user which criteria matter most if they have not said (AskUserQuestion with a few options: missions,
   pay, place and commute, school rhythm, team and mentoring, company stability, career prospects).
3. A table, one column per offer, one row per criterion, with facts from the offers only; unknown stays "non précisé".
4. A short reading: where each offer is clearly better, what is still unknown and worth asking. The decision is the
   user's: no ranking unless they ask for one.
