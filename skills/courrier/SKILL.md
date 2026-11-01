---
name: courrier
description: Read recruiter answers (acknowledgements, refusals, interview requests) in the user's mailbox through their mail connector and propose status changes. Use when the user asks whether recruiters answered, to check their mail, or to sync applications with their inbox.
argument-hint: "[gmail|outlook] [jours]"
---

# Recruiter mail

Speak to the user in their language. This skill reads only; it changes a status only after the user says yes to that
change, and it never sends, drafts, moves or deletes a mail.

1. `kandid chemins` for the data folder, and read the `mail` section of `config.yaml` (defaults apply when absent:
   60 days, one query per connector).
2. Find a connected mail connector: Gmail (`search_threads`) or Microsoft 365 (`outlook_email_search`). Use the one
   named in "$ARGUMENTS", else every one available. If none is connected, say which connector to add in Claude's
   settings and stop.
3. Search with the configured query, `{days}` replaced by the number of days:
   - Gmail: `search_threads` with that query, `pageSize` 50, view with subject and snippet.
   - Microsoft 365: `outlook_email_search` with the query, `afterDateTime` "<days> days ago", `limit` 25, then follow
     `nextCursor` up to 5 pages: job alerts fill the first pages.
   Never open full bodies unless a preview is too short to tell a refusal from an acknowledgement, and then only that
   mail.
4. Write `<data>/courrier/mails.json`: a list of `{source, id, sender, subject, preview, date, url}` (sender address,
   subject, preview text, ISO date). Nothing else from the mail.
5. `kandid courrier analyser <data>/courrier/mails.json --json`.
6. Report, newest first:
   - proposals (`target` set): date, kind, company, current status then proposed status, subject;
   - answers matched to no application: offer to record them (`kandid offre ajouter`, then `kandid offre statut`);
   - how many alerts and newsletters were ignored. If the user expected an answer that is missing, look for the
     pattern of `mail.ignore_senders` or `mail.ignore_subjects` that hides it and suggest editing `config.yaml`;
     likewise, a new kind of alert gets a pattern there, never a code change.
7. Ask which proposals to apply. For each accepted one:
   `kandid offre statut <id> <target> --date <day of the mail> --note "mail du <day> : <subject>"`.
8. Delete `<data>/courrier/mails.json` once done: it holds mail metadata the database does not need.

For a refusal, add one factual line (no comfort speech) and, when it is the third refusal for the same kind of role,
suggest `/kandid:bilan`.
