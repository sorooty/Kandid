---
name: setup
description: Set up or update the user's Kandid workspace. Asks their preferences, builds profile.yaml from their existing CV section by section, writes config.yaml, CLAUDE.md and A_SAVOIR.md, proposes Claude Code permissions and registers the scheduled tasks.
disable-model-invocation: true
---

# Kandid setup

Speak French unless the user writes in another language. Ask with AskUserQuestion, a few questions per call, and
always put the default first, marked "(Recommandé)". Explain in one sentence why each choice matters. Never write in
the master CV folder. Never put profile content into a web search or a connector.

## 1. Where things are

Run `kandid chemins`. If `config.yaml` exists there, this is an update: read it, show the current answers, ask what to
change, and keep the rest.

Ask (defaults in brackets):
- data folder [`~/.kandid`, shown expanded], where Kandid keeps the profile, settings, database and reports;
- applications folder [`<data>/applications`], where CVs and letters land;
- master CV folder, read-only for Kandid [none], and the CV file to import from it, or "start from scratch".

Paths are absolute in the files you write. If the data folder is not the default, tell the user the proposed
settings (step 4) are needed so `kandid` finds it.

## 2. Profile from the CV

Follow [import.md](import.md). The fictional example profile, for its shape only, is
`${CLAUDE_PLUGIN_ROOT}/examples/camille/profile.yaml`. Write `<data>/profile.yaml` only after the user has validated every section, then run
`kandid validate <data>/profile.yaml` and fix what it reports. If `profile.yaml` exists, ask whether to keep it,
re-import, or edit one section.

## 3. Search and tasks

Ask, offering choices drawn from the profile when it helps (never assume a domain):
- contracts sought (alternance, stage, cdi, cdd, interim, freelance) and, for alternance or stage, duration and
  school/work rhythm (these go into the profile header subtitle, after the user agrees on the wording);
- area: city [profile city], radius [30 km], remote offers accepted [no];
- keywords: 3 to 6, proposed from the profile's titles and skills, and words to exclude;
- offer sources: La bonne alternance, France Travail, Adzuna, company career pages (on); LinkedIn guest (off by
  default: its terms forbid automated access, the user turns it on knowingly). API keys stay in environment
  variables, never in the chat: name the variables from `config.yaml` and say how to set them on Windows
  (`setx NAME value` in a new terminal);
- scheduled tasks: offer watch [08:30], follow-ups [09:00], evening digest [19:00], each can be turned off. Say that
  each run costs at most 0.50 USD and 30 turns on their Claude plan (editable), that tasks only prepare, and that the
  computer must be on.

## 4. Write the files

1. Write the draft config to `<data>/setup-brouillon.yaml`, same schema as `config.yaml`, omitting defaults:
   `paths` (`data`, `applications`, `master`), `watch` (`contracts`, `keywords`, `exclude`, `area` with `city`,
   `radius_km`, `remote`; `sources.<name>.enabled`), `tasks` (`veille`, `relances`, `digest`, each `enabled` and
   `at: "HH:MM"`). Do not search the plugin's code for it.
2. `kandid setup ecrire <data>/setup-brouillon.yaml --json`. For each file reported `différent`, show the diff
   summary and ask whether to replace it; rerun with `--ecraser <file>` for those accepted.
3. Show the proposed `.claude/settings.json` (it is in the output's `diff` or, when new, explain its rules: `kandid`
   commands allowed, destructive commands refused, master folder protected even if a hook fails). Write it only after
   an explicit yes: rerun with `--settings`.
4. Delete the draft.

## 5. Tasks and first run

1. If tasks are enabled and the user agrees: `kandid taches installer`, then `kandid taches lister` to show them.
   Outside Windows, point to the cron section of `A_SAVOIR.md` instead.
2. Tell the user to open `<data>/A_SAVOIR.md`, and to start Claude Code from the data folder from now on.
3. Suggest a first `/kandid:veille`.
