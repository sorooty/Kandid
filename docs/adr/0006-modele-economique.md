# 0006 : Modèle économique freemium

- Statut : Accepté (grille tarifaire à définir dans une spec dédiée)
- Date : 2026-10-22

## Contexte

Le public est étudiant, au budget limité, et la recherche est saisonnière (en gros de février à septembre pour l'alternance). Il faut attirer largement et convertir sans pratiques trompeuses.

## Décision

- Gratuit : suivi des candidatures illimité, quelques générations IA par mois.
- Pass saison : accès étendu sur une durée limitée, aligné sur la période de recherche.
- Mensuel étudiant à prix d'appel bas.
- Parrainage récompensé en crédits IA.
- À moyen terme : licences écoles / CFA.

## Conséquences

- Quotas et droits gérés côté serveur, jamais côté client.
- Aucun dark pattern : résiliation en un clic, pas de faux compte à rebours.
- Les coûts IA par utilisateur (`ai_run`) servent à fixer les prix et les quotas.
