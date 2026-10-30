---
name: relance
description: Find applications sent 7 or 14 days ago without an answer and draft follow-up messages. Never sends anything.
disable-model-invocation: true
---

# Follow-ups

1. `kandid suivi --json`; keep the items whose action starts with "relancer" or "seconde relance".
2. For each, read `kandid offre voir <id>` and the letter in `<work>/<id>/letter.yaml` (`kandid chemins`).
3. Draft a short follow-up (under 120 words, same language as the application): recall the role and the date sent,
   one sentence of renewed interest tied to the offer, availability for a call. No new claim beyond the profile, no
   pressure. A second follow-up is shorter and the last one.
4. Show the drafts. With a mail connector, you may create drafts only; sending stays with the user and any send tool
   asks for their confirmation.
5. Once the user confirms a follow-up was sent: `kandid offre statut <id> followed_up`.
