# Spec: mail follow-up and history import

## Problem

The author tracked 31 applications in a throwaway web page while Kandid's database stayed empty: the page, a copy in
the browser and the files on disk disagreed within a day. Answers from recruiters (acknowledgements, refusals,
interview requests) arrive by mail, in Gmail or Outlook, buried under job alerts and newsletters; the author read
them one by one and updated the statuses by hand. Every user of Kandid will meet the same two problems: bringing the
applications already sent into Kandid, and keeping statuses in line with the mailbox.

## User story

As a student, I import the applications I already sent once, then I run `/kandid:courrier` every few days: Kandid
reads my recruiter mails through the mail connector I already have in Claude, hides alerts and newsletters, and
proposes "refusal from Renault on 28/10, move the application to Refus?" for each answer it recognizes. I accept or
ignore each proposal; nothing changes without my yes.

## Design

One source of truth: the SQLite database in the user's data folder (ADR 0011). The CLI stays deterministic and
offline; the skill does the reading through MCP and the conversation.

```
mail connector (Gmail, Microsoft 365)  ->  /kandid:courrier writes mails.json
mails.json  ->  kandid courrier analyser  ->  suggestions (JSON)
user says yes  ->  kandid offre statut <id> <statut> --date <jour du mail> --note "..."
past applications (JSON)  ->  kandid historique  ->  offers, applications, events
```

- `kandid_tools/mail.py`: pure functions. `is_noise` drops alerts and newsletters (sender and subject patterns),
  `classify` gives `rejection`, `interview`, `acknowledgement` or `other` from keyword lists, `suggest` matches each
  mail to an application by the normalized company name (the company part of `dedup.fingerprint`, the longest match
  wins) and proposes the target status only when `status.can_transition` allows it. An acknowledgement moves "Prêt"
  to "Envoyée"; on an application already sent it is reported, not proposed.
- `config.yaml` gains a `mail` section (`MailConfig`): days to look back, one search query per connector, noise
  patterns and keyword lists. Defaults cover French and English; a user who receives other alerts adds a pattern
  instead of editing code.
- `kandid offre statut` gains `--date`: a refusal is dated by its mail, not by the day it was recorded, so the
  answer delays in `kandid bilan` stay true.
- `kandid_tools/history.py` and `kandid historique <fichier.json>`: past applications (company, title, status, date,
  link, location, contract, contact, notes) become an offer of source `manuel`, an application with that status and
  dated events. An offer already in the database (same fingerprint) is skipped and reported. The file lives in the
  user's data folder, never in the repository.
- The database gets a schema version (`PRAGMA user_version = 1`) before real data lands, as planned in the watch
  spec.

### CRM (artifact view, ADR 0016)

The CRM is a Claude artifact that shows the applications of the SQLite database; the React app is postponed. The
interface validated with the author: neutral background, the app in one white card, pill tabs (Vue d'ensemble,
Candidatures), three figures with weekly deltas, a dot chart of applications per day over 30 days (sent and prepared
in two colors), the table with status tabs and a column with the next actions. The artifact template and its sync
skill get their own spec; they are not part of this branch.

## Scope

In: `mail.py`, `history.py`, `MailConfig`, `kandid courrier analyser`, `kandid historique`, `--date` on
`kandid offre statut`, schema version, skills `/kandid:courrier` and `/kandid:importer`, help table, tests on
fictional mails and applications.

Out: the API and the React app (phases 6 and 7), reading mail bodies (subject, sender and preview are enough to
classify), any automatic status change, sending or drafting mail from this skill (`/kandid:relance` does drafts).

## Acceptance criteria

- `pnpm check` green; `mail.py` and `history.py` unit tested, CLI commands tested with `CliRunner`.
- On a fixture of fictional mails, job alerts and newsletters are hidden, a refusal, an interview request and an
  acknowledgement are recognized, and only allowed transitions are proposed.
- `kandid historique` run twice imports nothing the second time.
- No real mail, address or company history in the repository.
