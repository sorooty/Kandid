# Kandid : audit & étude de faisabilité architecturale

> Statut : **Accepté**, décisions formalisées dans `docs/adr/0001` à `0006`
> Date : 2026-10-22
> Périmètre : choix techniques, risques, organisation du développement

---

## 1. État des lieux (audit)

| Élément | Constat |
|---|---|
| Code | Dossier `code/` vide, pas de dépôt git |
| Documentation | `Kandid_OBS/` et `other/` vides (hors périmètre code, non modifiés) |
| Poste de dev | Windows 11, Node 24, npm 11, pnpm 12, Python 3.14, Docker 29, Git 2.55 |
| Équipe | 1 développeur + Claude Code (desktop, puis CLI dans VS Code) |

**Conclusion** : projet greenfield, aucune dette, outillage complet. Toutes les options sont ouvertes ; le critère dominant est donc **la vélocité d'un développeur solo assisté par IA**, sans fermer de portes pour la suite.

---

## 2. Ce que Kandid doit faire (besoins et contraintes techniques)

| Domaine | Fonctionnalité | Contrainte technique induite |
|---|---|---|
| Profil | Import CV (PDF/DOCX) vers un profil structuré (formation, expériences, compétences, disponibilités, rythme d'alternance) | Extraction de documents + LLM, stockage de fichiers, données personnelles |
| Offres | Agrégation d'offres stage / alternance / job étudiant ; import d'une offre par URL ou copier-coller | Connecteurs API, jobs planifiés, déduplication |
| Matching | Score de pertinence entre offre et profil, explication du score | Recherche sémantique (vecteurs) + règles métier |
| Rédaction | CV adapté et lettre de motivation par offre, ton personnalisable | LLM, génération PDF, versionnage des documents |
| Suivi | Tableau de candidatures (kanban), statuts, relances, rappels d'entretien | CRUD temps réel, notifications, tâches planifiées |
| Préparation | Simulation d'entretien, questions types par entreprise | LLM conversationnel |
| Personnalisation | Thèmes, préférences, objectifs hebdo | Design tokens, préférences utilisateur |

### Spécificités métier à modéliser dès le départ
- **Alternance** : contrat d'apprentissage vs professionnalisation, rythme école/entreprise, date de rentrée, école/CFA, limite d'âge.
- **Stage** : convention obligatoire, durée, période, gratification au-delà de 2 mois.
- **Job étudiant** : volume horaire compatible avec l'emploi du temps, ponctuel vs récurrent.

Ces trois types ne se modélisent pas pareil : prévoir un modèle `offer` commun + un bloc d'attributs spécifiques par type.

---

## 3. Le point de faisabilité critique : « automatiser les candidatures »

C'est le vrai risque du projet, plus que la technique.

| Approche | Faisabilité | Risque | Verdict |
|---|---|---|---|
| Scraper LinkedIn / Indeed / WTTJ | Techniquement possible | **Violation des CGU**, blocages, contentieux (LinkedIn poursuit activement) | ❌ Rejeté |
| Candidature 100 % automatique (bot qui postule seul) | Fragile (formulaires hétérogènes, CAPTCHA) | CGU, image de « spam » auprès des recruteurs, nuit à l'étudiant | ❌ Rejeté |
| **API officielles** d'offres | Bonne | Faible | ✅ Socle |
| **Import manuel assisté** (URL / copier-coller, puis extraction IA) | Excellente, couvre 100 % des sites | Faible (action initiée par l'utilisateur) | ✅ Socle |
| **Extension navigateur** qui pré-remplit les formulaires sur la page que l'utilisateur consulte | Bonne | Faible (l'utilisateur valide et envoie) | ✅ Phase 2 |

**Principe directeur proposé : « Kandid prépare, l'étudiant valide et envoie. »** L'automatisation porte sur la recherche, le tri, la rédaction, le suivi et les relances, pas sur le clic final.

### Sources d'offres légitimes (France)
- **France Travail, API Offres d'emploi** (francetravail.io) : gratuite sur inscription, couvre stages et alternance.
- **La bonne alternance** (api.apprentissage.beta.gouv.fr) : API publique dédiée à l'alternance, inclut des entreprises susceptibles de recruter (candidature spontanée).
- **Adzuna API** : agrégateur avec palier gratuit.
- **Job boards publics des ATS** (Greenhouse, Lever, Ashby, SmartRecruiters...) : endpoints publics par entreprise, utiles pour les entreprises cibles.

> Conditions d'utilisation et quotas de chaque API à vérifier lors de l'intégration (ADR dédiée par connecteur).

---

## 4. Conformité (RGPD), non négociable

- CV, coordonnées, parcours = **données personnelles** ; certains utilisateurs peuvent être mineurs (alternance dès 16 ans).
- Hébergement **UE** (base, fichiers, fonctions serveur).
- Sous-traitants à lister (hébergeur, fournisseur LLM, emailing) avec leurs DPA.
- Export et suppression complète du compte dès le MVP (droit d'accès / à l'effacement).
- Ne jamais envoyer au LLM plus que nécessaire ; pas de données sensibles dans les logs.
- Isolation stricte des données par utilisateur au niveau base (Row Level Security).

---

## 5. Architecture recommandée

### 5.1 Vue d'ensemble

| Couche | Composants | Rôle |
|---|---|---|
| Clients | `apps/web` (Next.js), `apps/extension` (WXT, phase 3) | Interface, Server Actions, API |
| Packages partagés | `core`, `ai`, `db`, `ui` | Domaine, prompts et évaluations, schéma et migrations, design system |
| Services | Supabase UE (Postgres, pgvector, Auth, Storage, Cron, Queues), API Claude | Données, fichiers, tâches de fond, rédaction et extraction |
| Sources | France Travail, La bonne alternance, Adzuna... | Offres d'emploi |

Les clients appellent les packages partagés, qui seuls parlent aux services. Les connecteurs alimentent la base via des tâches planifiées.

### 5.2 Choix par couche

| Couche | Recommandation | Alternatives écartées | Pourquoi |
|---|---|---|---|
| Langage | **TypeScript partout** | Python (FastAPI) en backend | Un seul langage = un seul outillage, types partagés front/back/extension. Python ne se justifie que pour du ML lourd (non requis). |
| Repo | **Monorepo pnpm + Turborepo** | Multi-repos | Web + extension + packages partagés ; Claude Code voit tout le contexte. |
| Front + back | **Next.js (App Router)**, Server Actions / Route Handlers | SPA + API séparée, microservices | Un seul déploiement, SSR, excellent support par Claude. Microservices = surcoût injustifié en solo. |
| UI | **Tailwind CSS + shadcn/ui + design tokens** | MUI, Chakra | Composants possédés dans le repo (personnalisables), thèmes via variables CSS, accessibilité (Radix). |
| Base de données | **Postgres via Supabase (région UE)** + **pgvector** | Firebase, MongoDB | Relationnel adapté au domaine (profil, offres, candidatures), RLS pour l'isolation, vecteurs dans la même base. Postgres standard = réversible. |
| ORM / migrations | **Drizzle ORM** | Prisma | Léger, SQL-first, bien typé, compatible RLS. |
| Auth | **Supabase Auth** (email magique + Google) | Auth.js, Clerk | Intégré à la RLS, sans coût supplémentaire. |
| Fichiers | **Supabase Storage** (CV, documents générés) | S3 | Même périmètre de sécurité que la base. |
| Tâches de fond | **Supabase Cron + Queues (pgmq)** au départ | Inngest, Trigger.dev, Redis/BullMQ | Pas de service en plus ; migration vers Inngest/Trigger.dev si les workflows se complexifient. |
| IA | **API Claude** : Sonnet 5.5 pour la rédaction, Haiku 5.5 pour l'extraction / classification ; sorties structurées, prompt caching | Autres fournisseurs | Lecture native des PDF (import CV), qualité rédactionnelle en français. Abstraction légère dans `packages/ai` pour garder la main. |
| Embeddings | Recherche plein texte Postgres au MVP, puis **Voyage AI** + pgvector | Aucune | Ne pas sur-architecturer le matching avant d'avoir des données réelles. |
| PDF | **@react-pdf/renderer** | Puppeteer/Playwright | Pas de navigateur headless en serverless ; templates de CV en composants React. |
| Emails | **Resend** (React Email) | SendGrid | Simple, templates en React. |
| Hébergement | **Vercel (fonctions en région Paris)** + Supabase UE | VPS auto-géré | Zéro ops au démarrage ; paliers gratuits suffisants pour le MVP. |
| Mobile | **PWA** (installable, notifications) | React Native / Expo | Une seule base de code ; Expo envisageable plus tard en réutilisant `core` et `ai`. |
| Extension (phase 2) | **WXT** | Plasmo | Moderne, multi-navigateurs, TypeScript. |
| Observabilité | Sentry + logs Vercel ; suivi coûts/tokens IA en base | Datadog | Proportionné au scope. |

### 5.3 Modèle de données (première esquisse)

```
user 1:1 profile 1:n education / experience / skill / availability
user 1:n document (CV source, CV généré, lettre, versionnés)
offer (source, external_id, type: stage|alternance|job, attributs spécifiques, embedding)
user 1:n match (offer, score, explication)
user 1:n application (offer, statut, documents utilisés, dates)
application 1:n event (relance, entretien, réponse, note)
company 1:n offer ; company 1:n contact
ai_run (type, modèle, tokens, coût, durée), pour la maîtrise des coûts
```

Pipeline de statuts : à postuler, envoyée, relancée, entretien, puis offre, refus ou sans réponse.

### 5.4 Structure du monorepo

```
code/
  apps/
    web/              Next.js
    extension/        (phase 3)
  packages/
    core/             logique métier pure (testable sans base ni réseau)
    ai/               prompts versionnés, schémas, évaluations
    db/               schéma Drizzle, migrations, politiques RLS
    ui/               design system
  supabase/           config locale, migrations SQL, seed
  docs/
    architecture/     ce document
    adr/              décisions d'architecture (une par fichier)
    specs/            spécifications des fonctionnalités
  .claude/
    settings.json     permissions et hooks partagés
    agents/           sous-agents du projet
    commands/         commandes slash du projet
  .github/workflows/  CI
  CLAUDE.md           mémoire projet pour Claude Code
```

---

## 6. Faisabilité : synthèse

| Axe | Évaluation | Commentaire |
|---|---|---|
| Technique | 🟢 Élevée | Briques matures, aucune R&D nécessaire. |
| Données d'offres | 🟡 Moyenne | Couverture partielle via API officielles ; compensée par l'import manuel et l'extension. |
| Juridique | 🟡 Moyenne | Maîtrisable si on exclut le scraping et l'envoi automatique, et si le RGPD est traité dès le MVP. |
| Coûts | 🟢 Faibles au départ | Paliers gratuits hébergement ; l'IA est le seul coût variable, à mesurer (`ai_run`) et plafonner par utilisateur. |
| Charge solo | 🟡 Moyenne | Réaliste si le MVP reste resserré (cf. §7). |
| Qualité IA | 🟡 Moyenne | Exige des évaluations (jeu de CV/offres de référence) pour éviter les lettres génériques ou les hallucinations. |

**Verdict : faisable**, à condition de recentrer « l'automatisation » sur l'assistance (§3).

---

## 7. Découpage proposé

| Phase | Contenu | Objectif |
|---|---|---|
| **0. Fondations** | Monorepo, CI, Supabase local, auth, design system de base, CLAUDE.md, agents | Socle de dev solide |
| **1. MVP** | Import CV vers profil ; import d'offre par URL/texte ; génération lettre + CV adapté ; tableau de suivi ; export/suppression de compte | Une boucle complète utile pour un étudiant |
| **2. Recherche** | Connecteurs France Travail + La bonne alternance ; matching ; alertes | Trouver les offres à la place de l'étudiant |
| **3. Assistance active** | Extension navigateur (pré-remplissage) ; relances ; préparation d'entretien | Gain de temps maximal |
| **4. Croissance** | Statistiques personnelles, partage avec écoles, app mobile si nécessaire | Élargir l'usage |

---

## 8. Pratiques de développement (adaptées au solo + Claude Code)

| Pratique « entreprise » | Adaptation Kandid |
|---|---|
| Specs avant code | Une courte spec par fonctionnalité (`docs/specs/`), mode Plan de Claude Code avant implémentation |
| ADR | Toute décision structurante dans `docs/adr/NNNN-titre.md` (contexte, options, décision, conséquences) |
| Branches + PR | Trunk-based : `main` protégée, branches courtes `feat/...`, `fix/...`, PR même en solo |
| Revue de code | `/code-review` avant chaque merge + `/security-review` sur auth, RLS, uploads ; optionnellement l'action GitHub Claude sur les PR |
| Sous-agents projet | `reviewer` (lecture seule), `test-writer`, `db-migration` (RLS, migrations), `ux-copy` (textes FR) |
| Hooks | Format + lint automatiques après édition ; blocage de lecture des `.env` |
| Tests | Vitest (core, ai), Playwright (parcours critiques), **évaluations IA** dans `packages/ai` |
| CI | GitHub Actions : lint, typecheck, tests, build sur chaque PR |
| Commits | Conventional Commits (`feat:`, `fix:`, `chore:`...) |
| Travail parallèle | Worktrees git (une session Claude par branche) pour les tâches indépendantes |
| Secrets | `.env.local` jamais commité ; variables sur Vercel/Supabase |

---

## 9. Décisions à valider

1. **Principe « Kandid prépare, l'étudiant envoie »** (pas de scraping ni d'envoi automatique).
2. **Stack** : TypeScript, Next.js, Supabase UE, Drizzle, Tailwind/shadcn, API Claude.
3. **Plateforme** : web + PWA d'abord, extension en phase 2, natif mobile plus tard.
4. **Hébergement** du code : GitHub (privé ?).
5. **Modèle économique** envisagé (gratuit, freemium, écoles), qui influence le plafonnement des coûts IA.

Chaque point validé deviendra une ADR dans `docs/adr/`.
