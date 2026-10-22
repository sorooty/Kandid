# 07 : Tableau de bord

- Statut : À valider
- ADR liées : 0003, 0007

## Problème

Le tableau de suivi montre chaque candidature, mais pas la situation d'ensemble ni ce qu'il faut faire aujourd'hui. Une recherche d'alternance dure des mois : l'étudiant a besoin de voir qu'il avance pour garder le rythme.

## User stories

- En tant qu'étudiant, en ouvrant Kandid, je vois en un coup d'œil où j'en suis.
- Je sais ce que je dois faire aujourd'hui : relancer, préparer un entretien, envoyer une candidature.
- Je me fixe un objectif de candidatures par semaine et je vois si je le tiens.

## Périmètre

**Inclus**
- Page d'accueil après connexion.
- **Indicateurs** : candidatures actives, candidatures envoyées cette semaine, taux de réponse (réponses reçues sur candidatures envoyées), entretiens à venir.
- **À faire** : prochaines actions dépassées ou du jour (spec 05), et suggestions de relance pour les candidatures envoyées sans réponse depuis 10 jours.
- **Répartition par statut** : une barre horizontale simple, chaque segment renvoie au tableau filtré.
- **Objectif hebdomadaire** facultatif : nombre de candidatures visé, progression de la semaine.
- État vide soigné pour un nouvel utilisateur, avec un appel à l'ajout rapide (spec 06).

**Exclus**
- Graphiques d'évolution dans le temps, statistiques par source ou par type (après le MVP).
- Comparaison avec d'autres étudiants.
- Notifications et emails de rappel.

## Critères d'acceptation

- [ ] Tous les indicateurs viennent d'une seule requête agrégée côté serveur, sans requête par candidature.
- [ ] La page s'affiche en moins de 1 s avec 200 candidatures (LCP sous 2,5 s sur mobile).
- [ ] Chaque indicateur et chaque élément « À faire » mène à la liste filtrée correspondante.
- [ ] Le délai de 10 jours pour les suggestions de relance est une constante de `packages/core`, couverte par des tests.
- [ ] Les couleurs de statut restent lisibles en mode clair et sombre, et ne sont jamais la seule façon de distinguer un statut.

## Données

- Calculé à partir de `application` et `application_event` (spec 05), rien de stocké en plus.
- `profile.weekly_goal` (facultatif).

## Questions ouvertes

- La semaine commence-t-elle le lundi ? Proposition : oui, convention française.
