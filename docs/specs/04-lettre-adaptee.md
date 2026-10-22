# 04 : Lettre adaptée et suggestions CV

- Statut : À valider
- ADR liées : 0005, 0006, 0007

## Problème

Écrire une lettre différente pour chaque offre prend du temps, et une lettre générique se repère tout de suite. L'étudiant a besoin d'une première version solide, fidèle à son parcours, qu'il peut ajuster.

## User stories

- En tant qu'étudiant, je génère depuis une candidature une lettre qui relie mon parcours à l'offre.
- Je choisis un ton et une longueur, je modifie le texte, puis je le copie ou je l'exporte en PDF.
- Je reçois quelques conseils concrets pour adapter mon CV à cette offre.

## Périmètre

**Inclus**
- Génération par Claude Sonnet à partir du profil (spec 02) et de l'offre (spec 03).
- Options : ton (sobre ou dynamique), longueur (courte ou standard).
- Affichage progressif du texte pendant la génération (streaming).
- Éditeur de texte simple, sauvegarde automatique, conservation des 3 dernières versions.
- Copie en un clic et export PDF avec les coordonnées de l'étudiant.
- Suggestions CV : 3 à 5 conseils ciblés (expérience à mettre en avant, mot-clé manquant, compétence à reformuler).
- Quota : 10 générations par mois et par utilisateur, compteur visible, message clair une fois atteint.

**Exclus**
- Régénération complète du CV, modèles de CV.
- Envoi de la lettre depuis Kandid (ADR 0001).
- Traduction en anglais.

## Critères d'acceptation

- [ ] La lettre ne mentionne aucun diplôme, expérience ou compétence absent du profil (évaluation automatique sur un jeu de référence).
- [ ] La lettre cite l'entreprise, le poste et au moins deux éléments précis de l'offre.
- [ ] Aucun caractère interdit par CLAUDE.md dans le texte généré, ni formule creuse.
- [ ] Le premier mot s'affiche en moins de 3 secondes.
- [ ] Le quota est vérifié côté serveur avant chaque génération.
- [ ] Chaque génération est tracée dans `ai_run`.

## Données

- `letter` : `user_id`, `application_id`, `content`, `tone`, `length`, `version`, `created_at`.
- `cv_suggestion` : `user_id`, `application_id`, `items` (JSON), `created_at`.
- Quota calculé à partir de `ai_run` sur le mois en cours.

## Questions ouvertes

- Une modification manuelle compte-t-elle comme une génération ? Proposition : non, seules les générations par l'IA sont décomptées.
