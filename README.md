<h1 align="center">Kandid</h1>

<p align="center">Alternance, stage, emploi : Claude prépare tes candidatures, tu les valides et tu les envoies.</p>

<p align="center">
  <a href="https://github.com/sorooty/Kandid/actions/workflows/ci.yml"><img src="https://github.com/sorooty/Kandid/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/licence-MIT-blue" alt="Licence MIT"></a>
  <img src="https://img.shields.io/badge/statut-r%C3%A9%C3%A9criture%20en%20cours-orange" alt="Statut : réécriture en cours">
</p>

## Kandid v2, en construction

Kandid devient un framework pour Claude Code, installé et lancé sur ta machine :

- un **plugin Claude Code** (commandes `/veille`, `/postuler`, `/suivi`, garde-fous) qui fait de Claude un assistant
  de recherche d'emploi rigoureux : il ne soumet rien, ne se connecte à rien à ta place et n'invente aucune compétence ;
- une **application CRM locale** pour suivre tes candidatures, avec tableau de bord et pipeline.

Tes données restent dans un dossier local, hors du dépôt. Les choix de conception sont dans [docs/adr](docs/adr),
à partir de l'[ADR 0011](docs/adr/0011-local-first-plugin-and-crm.md).

L'installation et le démarrage rapide arriveront avec les premières versions utilisables.

## Kandid v1

La première version (application web Next.js et Supabase) est conservée sur la branche
[`legacy`](https://github.com/sorooty/Kandid/tree/legacy) et le tag `v1-legacy`.

## Développement

Prérequis : Python 3.11 ou plus avec [uv](https://docs.astral.sh/uv/), Node.js 24 et pnpm.

```bash
pnpm install
uv sync
pnpm check
```

## Licence

[MIT](LICENSE)
