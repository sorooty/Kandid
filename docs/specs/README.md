# Specs

Une spec par fonctionnalité, créée avec la commande `/feature`. Elle tient sur une page et sert de référence pour l'implémentation et la revue.

## MVP ([ADR 0007](../adr/0007-perimetre-mvp.md))

| Spec | Fonctionnalité | Statut |
|---|---|---|
| [01](01-compte.md) | Compte | À valider |
| [02](02-profil-depuis-cv.md) | Profil depuis le CV | À valider |
| [03](03-import-offre.md) | Import d'offre | À valider |
| [04](04-lettre-adaptee.md) | Lettre adaptée et suggestions CV | À valider |
| [05](05-suivi-candidatures.md) | Suivi des candidatures, vue tableur, export | À valider |
| [06](06-ajout-rapide.md) | Ajout rapide et import d'un tableau existant | À valider |
| [07](07-tableau-de-bord.md) | Tableau de bord | À valider |

## Ordre d'implémentation

1. **01 Compte** : tout le reste en dépend.
2. **05 Suivi** puis **06 Ajout rapide** : l'outil est utile dès ce stade, même sans IA.
3. **07 Tableau de bord** : il s'appuie sur les données du suivi.
4. **03 Import d'offre**, puis **02 Profil** : premières briques IA.
5. **04 Lettre adaptée** : elle combine le profil et l'offre.
