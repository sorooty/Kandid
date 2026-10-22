# 0004 : Dépôt public sous licence FSL

- Statut : Accepté
- Date : 2026-10-22

## Contexte

Le projet doit être visible des recruteurs (commits, PR, ADR, workflow agentique) tout en restant un produit à potentiel commercial.

## Options

1. Dépôt privé + dépôt vitrine : protège le code, mais l'historique réel reste invisible.
2. Dépôt public sous MIT : visibilité maximale, aucune protection commerciale.
3. Dépôt public sous FSL-1.1-ALv2 : code lisible et modifiable, usage concurrent interdit pendant 2 ans, puis Apache 2.0.

## Décision

Option 3.

## Conséquences

- Aucune donnée réelle ni secret dans le dépôt : données de test fictives uniquement.
- Secret scanning et push protection GitHub activés, gitleaks en CI.
- La sécurité ne repose jamais sur l'opacité du code (les politiques RLS sont publiques).
- README, démo et backlog GitHub Projects soignés : ils font partie de la vitrine.
