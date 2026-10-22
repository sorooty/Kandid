# 0007 : Périmètre du MVP

- Statut : Accepté
- Date : 2026-10-22

## Contexte

La phase 0 est terminée. Il faut livrer une première version utile rapidement, testable par de vrais étudiants, sans disperser l'effort sur les phases 2 et 3.

## Options

1. MVP large : recherche d'offres, matching, extension et suivi. Plus séduisant, mais des mois avant le premier test.
2. MVP resserré sur une boucle complète : profil, puis offre, puis lettre adaptée, puis suivi. Livrable vite, chaque brique sert à la suivante.

## Décision

Option 2, avec ces choix :

- **Cible prioritaire** : étudiants en recherche d'alternance. Stages et jobs étudiants restent gérés via le type d'offre.
- **Fonctionnalités** : compte, profil depuis le CV, import d'offre, lettre adaptée avec suggestions pour le CV, suivi des candidatures avec vue tableur et export Excel, ajout rapide et import d'un tableau existant, tableau de bord simple (specs 01 à 07).
- **CV** : pas de régénération complète, seulement des suggestions ciblées par offre.
- **Paiement** : aucun. Un quota de 10 générations de lettre par mois et par utilisateur, configurable côté serveur.
- **Ton de l'interface** : tutoiement.
- **Charte graphique** : définie avant le premier écran.
- **Critère de réussite** : 10 étudiants testeurs suivent au moins 5 candidatures chacun dans Kandid.

## Conséquences

- Hors MVP : connecteurs d'offres, extension navigateur, relances automatiques, score de correspondance, préparation d'entretien, paiement, partage d'offres et fonctions communautaires.
- Les idées hors périmètre sont notées dans le vault (`Idées en vrac.md`) avant d'être éventuellement promues en spec.
- Le quota et la table `ai_run` donnent les coûts réels qui serviront à fixer les prix (ADR 0006).
- Toute fonctionnalité hors de cette liste passe par une nouvelle ADR ou attend la phase 2.
