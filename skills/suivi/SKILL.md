---
name: suivi
description: Show where each application stands and the next action for each. Use when the user asks about their pipeline, what to do next, or their applications in progress.
---

# Application follow-up

1. `kandid suivi --json`.
2. Group by status in the Kanban order (À voir, À préparer, Prêt, Envoyée, Relance, Entretien, Offre). One line per
   application: number, company, role, days since the last change.
3. Finish with the three most useful next actions (the oldest follow-ups due first, then interviews to prepare, then
   offers waiting to be sorted), each with its command.
4. When the user reports news ("j'ai envoyé", "entretien mardi", "refus"), record it with
   `kandid offre statut <id> <sent|interview|offer|rejected> --note "..."` and confirm.
