---
name: veille
description: Run the offer watch (enabled sources, filters, deduplication, scoring) and summarize the new offers. Use when the user asks for new offers, a watch run, or what came in today.
argument-hint: "[source]"
---

# Offer watch

Speak to the user in their language. Nothing is applied to or sent.

1. Run `kandid veille --json` (add `--source <name>` if the user named one in "$ARGUMENTS").
2. Report per source in one line each: offers read, kept, already seen, filtered; skipped sources with their reason
   (missing keys are set in environment variables named in `config.yaml`, never pasted in the chat); errors as given.
3. List the new offers, best score first: score, company, title, number. For the top five, add the justification and
   the points to check from `kandid offre voir <id>`.
4. Suggest next steps: `/kandid:postuler <id>` for the ones worth preparing, `kandid offre ecarter <id> --raison "..."`
   for the clear misses. Do not prepare or discard anything without the user's word.

If no source ran, explain what to configure (`kandid chemins` shows where `config.yaml` is) and stop.
