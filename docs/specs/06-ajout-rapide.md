# 06 : Ajout rapide de candidatures

- Statut : À valider
- ADR liées : 0003, 0007

## Problème

Saisir une candidature à la main est la corvée qui fait abandonner les outils de suivi : trop de champs, trop de clics, et on remet à plus tard. Si l'ajout n'est pas quasi instantané, le tableau de suivi devient faux et perd tout son intérêt.

Objectif : **une candidature ajoutée en moins de 10 secondes, en 3 actions au plus.**

## User stories

- En tant qu'étudiant, j'ajoute une candidature depuis n'importe quel écran, avec deux informations seulement.
- Je colle ce que j'ai sous la main (lien, texte, ou juste « Capgemini, alternance dev ») et Kandid remplit le reste.
- J'enchaîne plusieurs ajouts sans repasser par un formulaire vide.
- Je ramène dans Kandid le tableau Excel que je tenais déjà.

## Périmètre

**Inclus**
- **Ajout rapide accessible partout** : bouton fixe et raccourci clavier `N`, qui ouvrent un panneau compact sans quitter la page.
- **Champ intelligent unique** :
  - un lien ou un texte d'offre lance l'import de la spec 03 ;
  - un texte court (« Entreprise, poste ») est découpé en entreprise et intitulé, sans appel à l'IA.
- **Deux champs obligatoires** seulement : entreprise et poste. Tout le reste est facultatif et repliable.
- **Valeurs par défaut intelligentes** : type repris de l'onboarding, statut « À postuler » ou « Envoyée » via un interrupteur « J'ai déjà postulé », date du jour.
- **Enchaînement** : bouton « Ajouter et continuer » qui garde le panneau ouvert et conserve le type et le statut.
- **Dupliquer** une candidature existante pour une offre proche.
- **Import d'un tableau existant** (`.xlsx` ou `.csv`) :
  - détection automatique des colonnes (entreprise, poste, statut, date, lien, notes) ;
  - correction manuelle de la correspondance ;
  - aperçu avant import ;
  - conversion des statuts libres (« en attente », « refusé ») vers les statuts Kandid.
- **Partage depuis le téléphone** : sur Android, Kandid installé en PWA apparaît dans le menu « Partager » du navigateur, et le lien partagé ouvre l'ajout rapide pré-rempli.

**Exclus**
- Import depuis d'autres applications par leur API.
- Ajout par email transféré à Kandid (idée à étudier après le MVP).
- Partage depuis iOS (non pris en charge par Safari pour les PWA).

## Critères d'acceptation

- [ ] Un ajout avec entreprise et poste se fait en 3 actions au plus : ouvrir, saisir, valider.
- [ ] Le panneau s'ouvre en moins de 100 ms et le champ est sélectionné automatiquement.
- [ ] Le découpage « Entreprise, poste » fonctionne sans appel réseau à l'IA.
- [ ] Un import de 100 lignes depuis un tableau fictif de référence se termine sans perte, avec un rapport des lignes ignorées et de la raison.
- [ ] Les doublons (même entreprise et même poste, ou même lien) sont signalés avant validation.
- [ ] Tout le parcours est utilisable au clavier et sur un écran de 375 px.

## Données

- Réutilise `company`, `offer` (spec 03) et `application` (spec 05).
- `application.source` : `quick_add`, `offer_import`, `file_import`, `share`.

## Questions ouvertes

- Faut-il proposer un modèle de tableau à télécharger pour faciliter l'import ? Proposition : oui, le même format que l'export de la spec 05, pour qu'export et import soient symétriques.
