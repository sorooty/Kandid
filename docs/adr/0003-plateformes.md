# 0003 : Plateformes cibles

- Statut : Accepté
- Date : 2026-10-22

## Contexte

Les étudiants cherchent depuis leur téléphone comme depuis leur ordinateur. Maintenir plusieurs bases de code est hors de portée en solo.

## Décision

1. Web responsive + PWA (installable, notifications) dès le MVP.
2. Extension navigateur (WXT) en phase 3, pour le pré-remplissage.
3. App native (Expo) seulement si la PWA montre ses limites, en réutilisant `packages/core` et `packages/ai`.

## Conséquences

- Mobile-first dans l'interface dès la première maquette.
- La logique métier ne dépend jamais de Next.js : elle vit dans `packages/core`.
