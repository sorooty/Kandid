# 01 : Compte

- Statut : À valider
- ADR liées : 0002, 0004, 0007

## Problème

L'étudiant doit pouvoir entrer dans Kandid en quelques secondes, sans mot de passe à retenir, et garder le contrôle total sur ses données.

## User stories

- En tant qu'étudiant, je me connecte avec un lien reçu par email ou avec Google.
- Je renseigne en moins d'une minute ce que je cherche pour que Kandid s'adapte à moi.
- Je peux télécharger toutes mes données ou supprimer mon compte à tout moment.

## Périmètre

**Inclus**
- Connexion par lien magique (email) et par Google, via Supabase Auth.
- Onboarding en un écran : prénom, type recherché (alternance par défaut, stage, job étudiant), école ou formation, date de début souhaitée, rythme d'alternance (facultatif).
- Page « Mon compte » : modifier ces informations, se déconnecter, exporter ses données, supprimer son compte.
- Export : un fichier JSON avec profil, offres, candidatures, lettres et le CV d'origine.
- Suppression : effacement définitif des lignes en base et des fichiers stockés, après confirmation en tapant « SUPPRIMER ».

**Exclus**
- Mot de passe, connexion LinkedIn ou Apple.
- Comptes école ou multi-utilisateurs.

## Critères d'acceptation

- [ ] Un nouvel utilisateur arrive sur l'onboarding juste après sa première connexion, puis sur son tableau de suivi.
- [ ] Un utilisateur ne peut lire ni modifier aucune ligne d'un autre utilisateur (test RLS automatisé).
- [ ] L'export contient toutes les données de l'utilisateur et rien d'autre.
- [ ] Après suppression, aucune ligne ni aucun fichier lié à l'utilisateur ne subsiste (test automatisé).
- [ ] Les pages protégées redirigent vers la connexion si la session a expiré.

## Données

- `auth.users` (Supabase).
- `profile` : `user_id`, `first_name`, `search_type`, `school`, `start_date`, `work_study_rhythm`, `created_at`.

## Questions ouvertes

- Faut-il demander l'âge ? Utile pour la limite d'âge de l'apprentissage, mais c'est une donnée de plus. Proposition : non au MVP.
