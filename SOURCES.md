# Sources

Les documents, dépôts et API consultés pour concevoir Kandid, avec ce que chacun a apporté. Une source n'est listée
que si elle a réellement été lue.

## Projets qui ont inspiré Kandid

| Source | Ce qu'elle a apporté |
|---|---|
| [ai-job-search](https://github.com/ai-job-search-dev/ai-job-search) (MIT) | Framework de candidature sur Claude Code : séparation entre rédacteur et relecteur, contrôle d'intégrité des offres, guide de rédaction, structure et ton du README. |
| [job-hunt-kit](https://github.com/Tedywarhol/job-hunt-kit) | Contrôle du ton des lettres, garde-fou sur les refus, couverture des mots-clés, utilisation des API publiques des ATS. |
| [excalidraw-studio](https://github.com/CopilotKit/excalidraw-studio) (MIT) | Serveur MCP Excalidraw, pour les schémas de la documentation. |
| [excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill) | Skill Claude Code de schémas Excalidraw (aucune licence déclarée : étudié, non repris). |

## Claude Code

| Source | Ce qu'elle a apporté |
|---|---|
| [Plugins reference](https://code.claude.com/docs/en/plugins-reference) | Format de `plugin.json`, emplacement des skills, agents et hooks, variables `CLAUDE_PLUGIN_ROOT` et `CLAUDE_PLUGIN_DATA`. |
| [Plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces) et [marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference) | Format de `marketplace.json` et installation du plugin depuis le dépôt. |
| [Skills](https://code.claude.com/docs/en/skills) | En-tête des `SKILL.md`, `$ARGUMENTS`, espace de noms `/kandid:...`. |
| [Subagents](https://code.claude.com/docs/en/sub-agents) | Définition de l'agent relecteur. |
| [Hooks reference](https://code.claude.com/docs/en/hooks) | Garde-fous `PreToolUse` (protection du CV maître, blocage des envois). |
| [Configure permissions](https://code.claude.com/docs/en/permissions) | Règles `Edit` et `Read` sur chemins, réglages proposés par `/kandid:setup`. |
| [Run Claude Code programmatically](https://code.claude.com/docs/en/headless) et [CLI reference](https://code.claude.com/docs/en/cli-reference) | Tâches planifiées avec `claude -p` : format `stream-json`, outils autorisés, plafonds de tours et de budget. |

## Sources d'offres

| Source | Ce qu'elle a apporté |
|---|---|
| [API Apprentissage, spec OpenAPI](https://api.apprentissage.beta.gouv.fr/api/documentation/json), [explorateur](https://api.apprentissage.beta.gouv.fr/en/explorer/recherche-offre) et [CGU](https://api.apprentissage.beta.gouv.fr/en/cgu) | Recherche d'offres en alternance (La bonne alternance) : route, filtres, limites et conditions d'usage. |
| [Article JobsPipe sur l'API France Travail](https://jobspipe.dev/blog/france-travail-api) | Flux OAuth2 et route de recherche de l'API Offres d'emploi, vérifiés ensuite sur [francetravail.io](https://francetravail.io). |
| [Documentation Adzuna](https://developer.adzuna.com/docs/search) | Paramètres de recherche et champs d'une offre. |
| [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html) | Offres publiées par les entreprises sur Greenhouse. |
| [Lever Postings API](https://github.com/lever/postings-api) | Offres publiées sur Lever, hôte européen compris. |
| [Ashby public job posting API](https://developers.ashbyhq.com/docs/public-job-posting-api) | Offres publiées sur Ashby. |
| [Comparatif des API d'offres des ATS](https://dev.to/chaazee/comparing-the-job-posting-apis-of-greenhouse-lever-ashby-smartrecruiters-and-recruitee-2026-4b60) | Routes publiques de SmartRecruiters et Recruitee, pagination. |
| [Page API de Jooble](https://jooble.org/api/about) | Source écartée : accès sur formulaire, sans documentation ni conditions publiques. |

## Outils

| Source | Ce qu'elle a apporté |
|---|---|
| [Réglages de uv](https://docs.astral.sh/uv/reference/settings/) | Âge minimal des paquets Python (`exclude-newer`). |
| [Server-Sent Events dans FastAPI](https://fastapi.tiangolo.com/tutorial/server-sent-events/) | Suivi en direct des exécutions de Claude dans l'API locale. |
| Releases de [actions/checkout](https://github.com/actions/checkout/releases), [setup-uv](https://github.com/astral-sh/setup-uv/releases), [setup-node](https://github.com/actions/setup-node/releases), [pnpm/action-setup](https://github.com/pnpm/action-setup/releases) et [gitleaks-action](https://github.com/gitleaks/gitleaks-action/releases) | Versions épinglées de l'intégration continue et détection de secrets. |
