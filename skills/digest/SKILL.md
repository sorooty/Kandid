---
name: digest
description: Summary of the day's job search, new offers, applications waiting, follow-ups due and tomorrow's actions. Use when the user asks what happened today or what to do tomorrow; also run by the evening scheduled task.
---

# Daily digest

Speak French unless the user writes in another language. Read only; nothing is prepared, sent or changed.

1. `kandid bilan --jours 1 --json`: offers found and applications sent today, answers.
2. `kandid offres --status to_review --json --limit 10`: offers waiting for a decision, best score first.
3. `kandid suivi --json`: applications and their next action; keep those with an action other than "attendre".

Write a short digest, at most 20 lines:
- **Aujourd'hui**: offers found, applications sent, answers received, in one or two lines.
- **À décider**: the five best offers waiting, with score, company, title and number; suggest `/kandid:postuler <id>`.
- **Demain**: follow-ups due (`/kandid:relance`), interviews to prepare (`/kandid:prep-entretien <id>`), applications
  ready to send by the user.

If nothing happened and nothing is due, say so in one line.
