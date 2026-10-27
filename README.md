<!-- Bannière à venir, une fois la charte graphique définie. -->
<h1 align="center">Kandid</h1>

<p align="center">Stage, alternance, job étudiant : des candidatures préparées, un suivi clair.</p>

<p align="center">
  <a href="https://github.com/sorooty/Kandid/actions/workflows/ci.yml"><img src="https://github.com/sorooty/Kandid/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/licence-FSL--1.1--ALv2-blue" alt="Licence FSL-1.1-ALv2"></a>
  <img src="https://img.shields.io/badge/Next.js-16-black?logo=nextdotjs" alt="Next.js 16">
  <img src="https://img.shields.io/badge/TypeScript-5-3178c6?logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/statut-en%20d%C3%A9veloppement-orange" alt="Statut : en développement">
</p>

<p align="center">
  <a href="#à-propos">À propos</a> |
  <a href="#fonctionnalités">Fonctionnalités</a> |
  <a href="#démarrage">Démarrage</a> |
  <a href="#architecture">Architecture</a> |
  <a href="#feuille-de-route">Feuille de route</a> |
  <a href="#contribuer">Contribuer</a>
</p>

## À propos

Chercher un stage, une alternance ou un job étudiant prend un temps fou : des offres éparpillées, une lettre à réécrire pour chaque entreprise, des relances qu'on oublie. Kandid regroupe tout au même endroit.

Kandid prépare, l'étudiant décide. L'application trouve et trie les offres, adapte le CV et la lettre à chacune et suit chaque candidature jusqu'à la réponse. L'envoi reste toujours entre les mains de l'étudiant : pas de scraping, pas de candidature envoyée à sa place ([ADR 0001](docs/adr/0001-kandid-prepares-student-sends.md)).

## Fonctionnalités

| Fonctionnalité | Description | Statut |
|---|---|---|
| Profil depuis le CV | Import d'un CV PDF, extraction en profil structuré | Prévu (MVP) |
| Import d'offre | Coller un lien ou un texte, l'offre est analysée | Prévu (MVP) |
| Candidature adaptée | CV et lettre de motivation ajustés à chaque offre | Prévu (MVP) |
| Suivi | Vue par étapes ou en tableur, export Excel et CSV | Prévu (MVP) |
| Ajout rapide | Une candidature en moins de 10 secondes, import d'un tableau existant | Prévu (MVP) |
| Tableau de bord | Indicateurs, actions du jour, objectif hebdomadaire | Prévu (MVP) |
| Recherche d'offres | France Travail, La bonne alternance et autres sources officielles | Prévu |
| Extension navigateur | Pré-remplissage des formulaires de candidature | Prévu |

## Démarrage

**Prérequis :** Node.js 24 ou plus, pnpm 12.

```bash
git clone https://github.com/sorooty/Kandid.git
cd Kandid
pnpm install
pnpm dev
```

L'application est disponible sur http://localhost:3000.

| Commande | Rôle |
|---|---|
| `pnpm dev` | Lance l'application en développement |
| `pnpm check` | Lint, vérification des types et tests |
| `pnpm build` | Build de production |
| `pnpm format` | Formate le code avec Biome |

## Architecture

Monorepo pnpm et Turborepo, en TypeScript de bout en bout.

```
apps/
  web/            application Next.js (interface, Server Actions)
packages/
  core/           logique métier, indépendante du framework
docs/
  adr/            décisions d'architecture
  specs/          spécifications des fonctionnalités
.claude/          configuration Claude Code (agents, commandes, hooks)
```

**Stack :** Next.js 16, React 19, Tailwind CSS 4, Supabase (Postgres, hébergé en UE), Drizzle, API Claude, Biome, Vitest.

Chaque choix structurant est documenté et justifié dans [docs/adr](docs/adr).

## Feuille de route

- [x] **Phase 0 : fondations.** Monorepo, CI, conventions, outillage
- [ ] **Phase 1 : MVP.** Profil, import d'offre, candidature adaptée, suivi
- [ ] **Phase 2 : recherche.** Connecteurs d'offres, matching, alertes
- [ ] **Phase 3 : assistance.** Extension navigateur, relances, préparation d'entretien

## Contribuer

Le projet est développé avec Claude Code dans un workflow agentique : une spec, un plan, une branche courte, une revue par un agent dédié, puis une PR validée par la CI. Les conventions sont décrites dans [CLAUDE.md](CLAUDE.md).

Les commits suivent les [Conventional Commits](https://www.conventionalcommits.org/fr/), avec une description en français.

## Licence

Distribué sous [Functional Source License 1.1](LICENSE.md). Le code peut être lu, modifié et réutilisé, sauf pour proposer un service concurrent. Chaque version passe automatiquement sous licence Apache 2.0 deux ans après sa publication.
