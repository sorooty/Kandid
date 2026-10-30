---
name: taches
description: Show, run, schedule or remove Kandid's scheduled tasks (offer watch, follow-ups, evening digest). Use when the user asks about their scheduled or automatic tasks, wants one run now, or wants them turned off.
argument-hint: "[lister | lancer <veille|relances|digest> | installer | supprimer]"
---

# Scheduled tasks

Speak French unless the user writes in another language. Request: $ARGUMENTS (none means `lister`).

- **lister**: `kandid taches lister`, then for each task its hour and next run. Add the hours and on/off state from
  the `tasks` section of `config.yaml` (`kandid chemins` gives its path) when a task is missing from the scheduler.
- **lancer <tâche>**: say it uses the user's Claude plan (capped by `tasks.max_budget_usd` in `config.yaml`) and
  may take a few minutes, then `kandid taches lancer <tâche>`. Report the outcome, the cost and the report path, and
  summarize the report in three lines.
- **installer**: show the tasks and hours from `config.yaml` and ask for a yes (AskUserQuestion) before
  `kandid taches installer`. To change an hour or turn a task off, edit the `tasks` section of `config.yaml` first,
  after the user agrees on the change.
- **supprimer**: ask for a yes, then `kandid taches supprimer`, and confirm with `kandid taches lister`. Say that
  `config.yaml` keeps the settings, so `installer` brings them back.

Tasks only prepare: they never send, apply or log in. Outside Windows, `kandid taches` cannot register them: point to
the cron section of `A_SAVOIR.md`.
