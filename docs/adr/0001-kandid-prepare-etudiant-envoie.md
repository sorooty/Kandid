# 0001 : Kandid prépare, l'étudiant envoie

- Statut : Accepté
- Date : 2026-10-22

## Contexte

L'objectif est d'automatiser la candidature. Les grands sites d'emploi (LinkedIn, Indeed, Welcome to the Jungle) interdisent le scraping dans leurs CGU, et un bot qui postule seul se heurte aux formulaires hétérogènes, aux CAPTCHA et à une image de spam côté recruteurs.

## Options

1. Scraping + envoi automatique : couverture maximale, risque juridique et réputationnel élevé.
2. API officielles + import manuel assisté + extension de pré-remplissage : couverture un peu moindre, risque faible.

## Décision

Option 2. Kandid automatise la recherche, le tri, la rédaction, le suivi et les relances. L'étudiant valide et envoie lui-même chaque candidature.

## Conséquences

- Sources d'offres : France Travail, La bonne alternance, Adzuna, job boards publics des ATS, import par URL ou copier-coller.
- Chaque connecteur fait l'objet d'une ADR (CGU, quotas).
- L'extension navigateur (phase 3) agit uniquement sur la page ouverte par l'utilisateur.
