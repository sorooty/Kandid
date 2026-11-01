---
name: importer
description: Bring applications sent before Kandid (spreadsheet, notes, another tracker) into Kandid's database. Use when the user starts with Kandid and already applied somewhere, or shares a list of past applications.
disable-model-invocation: true
argument-hint: "[fichier]"
---

# Import past applications

Speak to the user in their language.

1. Read the source the user gives ("$ARGUMENTS", an attached file, or a list pasted in the chat). It stays where it is;
   never copy it into the repository.
2. Build `<data>/import/historique.json` (`kandid chemins` gives `<data>`): a list of objects with `company`, `title`,
   `status` and, when known, `sent_on` (AAAA-MM-JJ), `url`, `location`, `contract` (`alternance`, `stage`, `cdi`,
   `cdd`, `interim`, `freelance`), `contact`, `notes`. Status values: `ready` (prepared, not sent), `sent`,
   `followed_up`, `interview`, `offer`, `rejected`, `archived` (dropped or blocked); French labels such as "Envoyée"
   or "Refus" are accepted too. Leave a field out rather than guess it.
3. Show the user a short table of what will be imported and ask for a yes.
4. `kandid historique <data>/import/historique.json`, then report the imported count and the ones already known.
5. Suggest `/kandid:courrier` to catch answers received since, then `/kandid:suivi`.
