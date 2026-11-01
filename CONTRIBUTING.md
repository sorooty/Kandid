# Contribuer à Kandid

Toute personne est la bienvenue pour proposer une idée, signaler un problème ou
améliorer Kandid. Il n'est pas nécessaire de savoir coder pour participer :
une idée bien expliquée peut déjà aider le projet.

## La charte de Kandid

Les contributions doivent respecter les principes du projet :

- **Kandid prépare, la personne décide et envoie.** Aucune contribution ne doit
  automatiser l'envoi d'une candidature, d'un message ou d'un formulaire sans
  validation explicite de la personne.
- **Les données restent locales.** Ne partagez jamais de CV, de profil,
  d'adresse, de candidature ou de journal contenant des données personnelles.
  Les exemples et les tests utilisent uniquement des données fictives.
- **Aucune expérience n'est inventée.** Les documents produits doivent rester
  fidèles aux informations fournies par la personne.
- **Les échanges sont respectueux et constructifs.** Les questions, les
  désaccords et les propositions sont les bienvenus, sans attaque personnelle.

## Proposer une fonctionnalité

Avant de commencer à coder une nouvelle fonctionnalité, ouvrez une discussion
sur [GitHub Discussions](https://github.com/sorooty/Kandid/discussions). Cela
permet de vérifier que l'idée répond à un besoin, qu'elle correspond aux
principes de Kandid et que son périmètre est clair.

Une proposition peut rester courte. Expliquez simplement :

1. le problème rencontré et les personnes concernées ;
2. le résultat attendu ou un exemple d'utilisation ;
3. les contraintes ou les questions encore ouvertes.

Attendez un premier échange avec les mainteneurs avant d'engager un travail
important. Une petite correction de documentation ou un correctif ciblé n'a pas
besoin d'une discussion préalable.

## Préparer une pull request

Une fois la proposition clarifiée :

1. créez une branche courte à partir de `main`, par exemple
   `feat/recherche-par-ville` ou `fix/filtre-offres` ;
2. limitez la pull request à un objectif compréhensible et reliez-la à la
   discussion ou au problème concerné ;
3. décrivez brièvement le problème, la solution et les vérifications effectuées ;
4. signalez les changements visibles par les personnes qui utilisent Kandid.

Gardez la pull request aussi simple que possible. Les captures d'écran sont
utiles pour un changement visuel, mais ne doivent contenir aucune donnée
personnelle.

## Vérifications

Depuis la racine du dépôt, installez les dépendances si nécessaire, puis lancez
les vérifications :

```bash
pnpm install
uv sync
pnpm check
```

`pnpm check` lance le lint et les tests du projet. Si vous ne pouvez pas lancer
une vérification, indiquez-le dans la pull request.

## Besoin d'aide ?

Vous pouvez poser vos questions dans la discussion liée à votre idée ou à votre
pull request. Une proposition n'a pas besoin d'être parfaite pour être utile :
le but est de la clarifier ensemble avant de décider de la suite.
