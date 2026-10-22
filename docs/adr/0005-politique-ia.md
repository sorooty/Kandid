# 0005 : Politique IA

- Statut : Accepté
- Date : 2026-10-22

## Contexte

L'IA est le cœur de la valeur (lettres, CV adaptés) et le seul coût variable. Les paliers gratuits des fournisseurs ont des quotas faibles et utilisent parfois les données pour l'entraînement, ce qui est incompatible avec des CV d'étudiants, parfois mineurs.

## Options

1. Modèles gratuits en production : coût nul, risques RGPD et fiabilité.
2. Modèles locaux en dev, modèles payants peu chers en production avec quotas utilisateur.

## Décision

Option 2 :

- Dev et tests : Ollama en local, données fictives uniquement.
- Production : API Claude. Haiku 5.5 pour l'extraction et la classification, Sonnet 5.5 pour la rédaction finale.
- Sorties structurées, prompt caching, plafond de dépense dans la console.
- Le « seuil gratuit » est un quota par utilisateur et par mois (voir ADR 0006).
- `packages/ai` expose une interface indépendante du fournisseur.

## Conséquences

- Chaque appel est tracé dans `ai_run` (modèle, tokens, coût, durée).
- Le minimum de données personnelles est envoyé au modèle ; rien de sensible dans les logs.
- Les prompts sont versionnés et couverts par des évaluations avant tout changement.
