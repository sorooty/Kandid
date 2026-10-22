# 03 : Import d'offre

- Statut : À valider
- ADR liées : 0001, 0005, 0007

## Problème

Les offres sont éparpillées sur des dizaines de sites. L'étudiant doit pouvoir ramener n'importe laquelle dans Kandid en un geste, quelle que soit sa source.

## User stories

- En tant qu'étudiant, je colle le lien d'une offre et Kandid en extrait l'essentiel.
- Si le lien ne fonctionne pas, je colle le texte de l'offre à la place.
- L'offre importée devient une candidature « À postuler » dans mon suivi.

## Périmètre

**Inclus**
- Champ unique acceptant une URL ou du texte brut.
- Pour une URL : récupération de la page côté serveur, à la demande de l'utilisateur uniquement, puis extraction du texte principal.
- Extraction par Claude Haiku : intitulé, entreprise, type (alternance, stage, job), lieu, télétravail, date de début, durée, rythme, rémunération si indiquée, compétences demandées, contact, date limite.
- Fiche modifiable avant enregistrement.
- Création automatique d'une candidature au statut « À postuler » (spec 05).
- Détection de doublon : même URL déjà importée par l'utilisateur.

**Exclus**
- Recherche d'offres, alertes, import en masse (phase 2).
- Contournement d'une page de connexion ou d'un CAPTCHA : dans ce cas on propose le copier-coller.

## Critères d'acceptation

- [ ] Sur 10 offres de référence (sites variés), les champs clés (intitulé, entreprise, type, lieu) sont corrects dans au moins 90 % des cas.
- [ ] La récupération d'URL est protégée contre le SSRF : http et https uniquement, adresses privées et locales refusées, délai de 10 s, taille maximale de 2 Mo.
- [ ] Un échec de récupération bascule vers le copier-coller avec un message clair.
- [ ] L'import complet prend moins de 8 secondes dans 90 % des cas.

## Données

- `company` : `user_id`, `name`, `website`.
- `offer` : `user_id`, `company_id`, `source_url`, `raw_text`, `title`, `type`, `location`, `remote`, `start_date`, `duration`, `rhythm`, `salary`, `skills`, `deadline`, `created_at`.
- Index unique sur (`user_id`, `source_url`).

## Questions ouvertes

- Conserve-t-on le texte brut de l'offre ? Proposition : oui, il sert à générer la lettre même si l'offre disparaît en ligne.
