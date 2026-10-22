# 02 : Profil depuis le CV

- Statut : À valider
- ADR liées : 0005, 0007

## Problème

Ressaisir son parcours est fastidieux. Le profil est pourtant la matière première de toutes les candidatures adaptées : il doit être complet et fidèle.

## User stories

- En tant qu'étudiant, j'importe mon CV et je retrouve mon parcours déjà rempli.
- Je corrige ce que l'IA a mal compris, et c'est ma version qui fait foi.

## Périmètre

**Inclus**
- Import d'un CV au format PDF, 5 Mo maximum, stocké dans un bucket privé.
- Extraction par Claude Haiku en sortie structurée : coordonnées, formations, expériences, compétences, langues, liens (portfolio, GitHub, LinkedIn).
- Validation du résultat avec zod avant enregistrement.
- Écran de relecture : chaque section est modifiable, ajoutable ou supprimable.
- Création manuelle du profil sans CV.
- Réimport d'un CV : remplace le profil après confirmation.

**Exclus**
- Formats DOCX, images, import depuis LinkedIn.
- Fusion intelligente entre l'ancien et le nouveau profil.

## Critères d'acceptation

- [ ] Sur un jeu de 5 CV fictifs de référence, au moins 90 % des champs sont extraits correctement (évaluation dans `packages/ai`).
- [ ] L'extraction n'invente aucune information absente du CV.
- [ ] Un PDF illisible ou trop lourd affiche un message clair et propose la saisie manuelle.
- [ ] Le contenu du CV n'apparaît dans aucun log.
- [ ] Chaque extraction est tracée dans `ai_run` (modèle, tokens, coût, durée).

## Données

- Storage : `cv/<user_id>/<fichier>.pdf`, accès limité au propriétaire.
- `profile` (spec 01) complété par `education`, `experience`, `skill`, `language`, `link`, chacune avec `user_id`.
- `ai_run` : `user_id`, `kind`, `model`, `input_tokens`, `output_tokens`, `cost`, `duration_ms`, `created_at`.

## Questions ouvertes

- Garde-t-on le PDF d'origine après extraction ? Proposition : oui, pour pouvoir relancer l'extraction, et il est supprimé avec le compte.
