# 05 : Suivi des candidatures

- Statut : À valider
- ADR liées : 0003, 0007

## Problème

Au-delà de dix candidatures, on perd le fil : qui a répondu, qui relancer, quand est l'entretien. C'est l'écran que l'étudiant ouvrira tous les jours.

## User stories

- En tant qu'étudiant, je vois toutes mes candidatures classées par étape.
- Je fais avancer une candidature d'un geste et je note ce qui s'est passé.
- Je sais immédiatement quelles candidatures demandent une action.
- Je bascule sur une vue tableur pour tout voir d'un coup, et j'exporte mes candidatures en Excel ou en CSV.

## Périmètre

**Inclus**
- Vue en colonnes par statut sur ordinateur, liste groupée par statut sur mobile.
- Vue tableur : une ligne par candidature, colonnes triables (entreprise, poste, type, statut, date d'envoi, dernier changement, prochaine action), choix des colonnes affichées, modification directe du statut et de la prochaine action dans la cellule.
- Export de la vue tableur en `.xlsx` et en `.csv` (UTF-8, compatible Excel), généré côté serveur, en respectant les filtres actifs.
- Statuts et transitions définis dans `packages/core` : À postuler, Envoyée, Relancée, Entretien, Offre, Refus, Sans réponse.
- Changement de statut par glisser-déposer (ordinateur) ou menu (mobile). Une transition non autorisée est refusée avec une explication.
- Carte : entreprise, poste, type, date du dernier changement, prochaine action.
- Fiche détaillée : offre, lettre, notes datées, historique des statuts.
- Champ « prochaine action » avec date, mis en avant quand elle est dépassée.
- Création manuelle d'une candidature : voir la spec 06.
- Filtre par type (alternance, stage, job) et recherche par entreprise.
- Archivage des candidatures terminées.

**Exclus**
- Rappels par email ou notification (après le MVP).
- Statistiques et indicateurs : voir la spec 07.
- Partage du tableau avec une école.
- Synchronisation avec Google Sheets.

## Critères d'acceptation

- [ ] Les transitions respectent exactement `canTransition` de `packages/core`, côté interface et côté serveur.
- [ ] Chaque changement de statut est enregistré avec sa date dans l'historique.
- [ ] Le tableau reste fluide avec 200 candidatures : liste paginée ou virtualisée, INP sous 200 ms.
- [ ] Tout est utilisable au clavier, et le glisser-déposer a une alternative accessible.
- [ ] L'écran est utilisable sur un téléphone de 375 px de large.
- [ ] Un export de 200 candidatures s'ouvre correctement dans Excel et LibreOffice (accents, dates, colonnes).
- [ ] L'export ne contient que les candidatures de l'utilisateur, filtrées comme à l'écran.

## Données

- `application` : `user_id`, `offer_id` (facultatif), `status`, `next_action`, `next_action_at`, `archived`, `updated_at`.
- `application_event` : `user_id`, `application_id`, `kind` (statut, note), `from_status`, `to_status`, `note`, `created_at`.
- Index sur (`user_id`, `status`) et (`user_id`, `next_action_at`).

## Questions ouvertes

- Faut-il un statut « Brouillon » avant « À postuler » ? Proposition : non, « À postuler » suffit.
