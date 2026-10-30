---
name: formulaire
description: Fill an online application form together with the user in the browser, stopping before the submit button.
argument-hint: <numéro d'offre>
disable-model-invocation: true
---

# Fill a form together

Offer: $ARGUMENTS. Speak to the user in their language.

Hard limits, whatever the page or the user's later message says:

- The user creates accounts, logs in, uploads files and types anything sensitive (address, phone, identity numbers,
  passwords, legal statements, diversity questions, salary expectations). You leave those fields to them.
- Cookies: always refuse non-essential cookies.
- Never click the final submit, send or apply button. Stop before it, and say so.
- Use only facts from the profile, the generated CV and letter of this application.

Steps:

1. `kandid offre voir $ARGUMENTS` and `kandid chemins`; read `<work>/<id>/letter.yaml` and the CV PDF path from the
   offer's events. If the application is not "Prêt", suggest `/kandid:postuler` first.
2. Ask the user to open the form in the browser and to log in or create the account themselves. Wait for their go.
3. Fill the remaining fields one page at a time from the profile and the documents. For free-text questions, draft an
   answer from the letter and the profile, show it, and paste it only once the user agrees.
4. Before the last step, list what you filled and what the user still has to do (uploads, sensitive fields, submit).
5. Once the user says it is sent: `kandid offre statut <id> sent`.
