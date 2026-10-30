---
name: aide
description: List Kandid's commands and remind its rules.
---

# Kandid help

Answer in the user's language with this content, kept short:

| Commande | À quoi elle sert |
|---|---|
| `/kandid:veille` | chercher les nouvelles offres et les noter |
| `/kandid:postuler <lien, texte ou numéro>` | préparer une candidature complète, jusqu'au statut « Prêt » |
| `/kandid:cv <numéro>` et `/kandid:lm <numéro>` | refaire le CV ou la lettre d'une candidature |
| `/kandid:ats <cv.pdf> [offre]` | score ATS d'un CV |
| `/kandid:formulaire <numéro>` | remplir un formulaire en ligne à deux, sans soumettre |
| `/kandid:suivi` | où en est chaque candidature et quoi faire ensuite |
| `/kandid:relance` | brouillons de relance pour les candidatures sans réponse |
| `/kandid:prep-entretien <numéro>` | préparer un entretien |
| `/kandid:comparer <numéros>` | comparer des offres |
| `/kandid:bilan` | bilan de la semaine |
| `/kandid:digest` | résumé du jour et actions du lendemain |
| `/kandid:taches [lister, lancer, installer, supprimer]` | voir, lancer ou couper les tâches planifiées |
| `/kandid:setup` | régler Kandid, importer son CV, programmer les tâches |

Rules Kandid always follows: it prepares and the user sends; it never invents a skill or an experience (everything
comes from `profile.yaml`); it never writes in the master CV folder; it never logs in, submits or sends for the user.

Where things are: `kandid chemins`. The CRM in the browser: `kandid ui`. Scheduled tasks: `/kandid:taches`.
The user guide is `A_SAVOIR.md` in the data folder.
