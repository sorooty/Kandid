# Spec: local database and offer watch (v2 phase 3)

## Problem

Offers are found by hand on several sites, noted in a markdown file, and checked against what was already seen by
memory. Nothing is deduplicated across sources, nothing is scored the same way twice, and an offer that disappears is
lost. Later phases (plugin, scheduler, app) need one local store of offers and applications and a deterministic
`kandid veille` to feed it.

## User story

As a student, I describe once what I look for (contracts, keywords or job codes, area, companies I follow) and which
sources I enable. `kandid veille` queries every enabled source, keeps only real matches, removes duplicates and offers
I already saw, scores each one /100 with a short justification and points to check, and stores them in the "À voir"
column. Nothing is sent and nothing is applied to.

## Scope

In:

- `db.py`: SQLModel on SQLite in the user data folder (`<data>/kandid.db`). Tables `offer` (source, external id,
  company, title, location, contract, url, description, dates, fingerprint, score, justification, points to check,
  other sources carrying it), `application` (one per offer, status from `status.py`, dates: an offer's place in the
  inbox is its application status), `event` (timeline of an application: found, discarded with a reason), `run`
  (each `kandid veille`: start, end, per-source counts, skips and errors). Indexes on every foreign key, on
  `(source, external_id)` (unique), `fingerprint`, `status`, score and dates. The `task` and `notification` tables
  wait for phases 5 and 6.
- `sources/`, one module per source behind a common interface (`search(client, watch, secrets) -> list[RawOffer]`, plus `covers_area(watch)` telling
  whether the source already searched within the wanted area), each response
  validated by pydantic, polite HTTP (httpx, timeout, user agent, one retry at most, stop on 429):

  | Source | Access | Covers | Default |
  |---|---|---|---|
  | La bonne alternance (API Apprentissage) | free account, Bearer token | work-study in France (LBA, France Travail, partners), by ROME code and area | on when a token is set |
  | France Travail, Offres d'emploi v2 | free app on francetravail.io, OAuth2 client credentials | every contract in France, by keywords and area | on when keys are set |
  | Adzuna | free app id and key | aggregator, France and 18 other countries, by keywords | on when keys are set |
  | Company career pages: Greenhouse, Lever, Ashby, SmartRecruiters, Recruitee | public, no key | first-party offers of the companies the user follows | on for listed companies |
  | LinkedIn guest | public pages, opt-in (ADR 0013) | everything LinkedIn shows logged out | off |
  | Manual import | `kandid offre ajouter` with a URL and pasted text | anything | always |

  Left out on purpose: Jooble (no public documentation or readable terms), Welcome to the Jungle, HelloWork, Indeed,
  JobTeaser (no public API, scraping forbidden by their terms), Arbeitnow (German market).
- Deduplication: exact on `(source, external_id)`, then a fingerprint of normalized company and title (accents, case,
  gender markers such as "H/F" removed) across sources; the first source seen wins, later ones are attached as links.
- Filters from `config.yaml`: wanted contracts (an unknown contract is kept and flagged), area (city or departments,
  or remote; skipped for sources that searched within the area), excluded words (in the title only), age, minimum
  score, already seen. Spontaneous-application entries (LBA `recruteurs_lba`) are not offers
  and are ignored.
- `scoring.py`: deterministic score /100: contract 25, keywords 25 (title, else description for less), skills
  stated in `profile.yaml` 25, area 15, freshness 10. An unknown value earns half its points and a point to check.
  One-line justification and a list of points to check (intermediary school, unknown contract, place or
  description). Required level and duration wait for a reliable source field. Domain neutral: it reads the profile and
  config, never a built-in IT vocabulary.
- CLI: `kandid veille [--source x] [--dry-run] [--json]`, `kandid offre ajouter`, `kandid offres [--status]`,
  `kandid offre ecarter <id> --raison`.
- Secrets (tokens, client ids, keys) read from environment variables named in `config.yaml`, never written to the
  data folder, never logged, never sent to Claude.

Out: skills and commands (phase 4), scheduling (phase 5), API and UI (phases 6 and 7), migration of the author's
history (phase 10), any action on an offer beyond reading it.

## Acceptance criteria

- `pnpm check` green. Each source is tested on recorded and anonymized responses (no network call in tests), including
  an error, an empty page and a malformed payload.
- Running `kandid veille` twice inserts nothing the second time; the same offer from two sources is stored once.
- A real `kandid veille` run locally with the user's keys returns scored offers in "À voir", with a `run` row giving
  per-source counts.
- No secret appears in the database, logs, CLI output or tests.

## Data touched

Writes `kandid.db` in the data folder. Reads `config.yaml`, `profile.yaml` and environment variables. Sends to each
enabled source only the search criteria (keywords, job codes, area), never profile content.

## Open questions

1. Secrets: environment variables (simple, works with the scheduler) or the Windows credential manager through the
   `keyring` package (safer at rest, one more dependency). Proposed: environment variables now, keyring later if
   wanted.
2. La bonne alternance searches by ROME job codes, not keywords. Proposed: the user lists codes in `config.yaml`, and
   `/setup` (phase 5) will help find them from the wanted jobs.
3. France Travail token URL and scope come from consistent third-party sources; the official page needs a logged-in
   account. They will be confirmed on the first real call with the user's keys.

## Known limits and follow-ups

- One page per search: France Travail returns at most 150 offers, La bonne alternance 150 per underlying source,
  Adzuna 50 per keyword. Enough for a daily watch with focused criteria; pagination comes if real runs hit the caps.
- France Travail `motsCles` gets the keywords comma-separated; whether they combine as AND or OR is checked on the
  first real call. La bonne alternance receives coordinates rounded to two decimals (about 1 km), never the exact
  address.
- Company boards are not searched by keyword: their postings are kept only when a keyword appears in the title or
  description. An offer with an unknown contract or place is kept and flagged rather than dropped.
- Same company and title count as one offer across sources; within one source, only when the place is the same too.
  Offers whose company is hidden are never merged.
- The data folder is `~/.kandid`, or `KANDID_HOME` when set (tests use it to stay away from real data).
- Before real data lands (phase 10): a schema version (`PRAGMA user_version`) and a migration step, since
  `create_all` does not alter existing tables. Phase 4: a pre-commit check rejecting user data files (`*.db`,
  `profile.yaml`, `config.yaml`) even when forced.
