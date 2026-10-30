# Kandid v2 inventory (phase 0)

Snapshot of what exists before the rewrite, what is kept, generalized or dropped, and why.
No personal data here: names, contacts, companies and dates from the author's own files are replaced by
placeholders (`<First>`, `<Last>`, `<Company>`).

Decisions already taken with the user (2026-10-30):

- The current state (including `feat/account`) is frozen as tag `v1-legacy` and branch `legacy`. The rewrite
  happens on `feat/v2-*` branches merged into `main` by PR, one per phase. CLAUDE.md workflow stays unchanged.
- LinkedIn guest source as an opt-in, disabled by default: no login, terms-of-use warning, 1.5 s pause between
  requests. A new ADR amends 0001 to record it as an exception the user enables knowingly. Default sources stay the
  public APIs (La bonne alternance, France Travail) plus manual import (URL or pasted text).
- License moves from FSL-1.1-ALv2 to MIT, with a new ADR superseding 0004.
- `import/candidatures-workflow.md` and `import/veille-alternance.md` are provided by the user in `import/`
  (excluded from git).

## 0. Current repository (Kandid v1)

| Area | Content | Verdict | Reason |
|---|---|---|---|
| `apps/web` (Next.js 16) | invitation sign-in, onboarding, account, data export, deletion | Dropped | v2 is local-first: no hosted instance, no auth, no Supabase |
| `packages/db`, `supabase/` | Drizzle schema, RLS, migrations, email templates | Dropped | Replaced by local SQLite (single user, data never leaves the machine) |
| `packages/core/application/status.ts` | status list and allowed transitions | Reused (ported) | Same rule set, extended to the 9 Kanban columns; tests ported to pytest |
| `packages/core/profile` | profile constants and validation | Reused (ideas) | Becomes the `profile.yaml` schema (pydantic) |
| `docs/adr` 0001, 0005 | prepare-not-send, AI policy | Kept | Still the founding rules of v2 |
| `docs/adr` 0002, 0003, 0006, 0007, 0008, 0010 | hosted stack, platforms, business model, MVP, restricted scope, Drizzle/RLS | Superseded | New ADRs: local-first plugin + CRM, SQLite, MIT |
| `docs/specs` 02 to 07 | CV import, offer import, letter, tracking, quick add, dashboard | Reused (content) | Rewritten as skill specs; the user stories still hold |
| `scripts/*banned-chars*`, `check-commit-msg.mjs`, `lefthook.yml` | banned characters, Conventional Commits | Kept | Writing and commit conventions are unchanged |
| `.claude/agents/code-reviewer.md` | reviewer agent | Kept, adapted | Checks Python and the new layout instead of RLS |
| `.claude/agents/db-guardian.md` | RLS and GDPR guardian | Adapted | Becomes a data-protection reviewer (user data folder, pre-commit leaks) |
| `.claude/commands/adr.md`, `feature.md` | dev workflow commands | Kept | Dev tooling for the Kandid repo itself, not part of the shipped plugin |
| `biome.json`, Vitest, CI workflow | lint, tests | Kept, extended | Front still TypeScript; Python gets ruff + pytest in the same CI |

## (a) Existing scripts (master folder, read-only)

Location: `<Drive>\<Job search>\<Master>\`.

| Script | Role | Inputs / outputs | Dependencies | Hard-coded, to generalize |
|---|---|---|---|---|
| `ats_check.py` | Deterministic ATS heuristic: format /100 (parsing 40, structure 30, content 30), plus offer keyword match; global = 50/50 | `CV.pdf [offre.txt]` in, plain text report on stdout | poppler (`pdfinfo`, `pdftotext`, `pdffonts`), stdlib | French city names in the location check; section names FR/EN; stop words; "first 2 lines of the offer are title and URL"; text output only (needs JSON for the UI) |
| `wrapcheck.py` | Flags `Label : ...` lines that wrap onto two lines in Skills / Certifications / Soft skills | `CV.pdf` in, text out | poppler | Section titles hard-coded in FR and EN; label regex length 45 |
| `gen_cv.py` | Builds the CV `.tex` from a per-offer `spec.py` plus common blocks; prepends a default project when fewer than 4 | `spec.py`, output `.tex` | `blocks.py`, `runpy` | Whole header (name, email, phone, city, links, PDF metadata), education, certifications, languages, hobbies, default project key, section order; `spec.py` is executable Python (unsafe as a data format) |
| `gen_lm.py` | Builds the cover letter `.tex` from a text body (line 1 recipient split by `\|`, line 2 subject, then paragraphs) | `corps.txt`, output `.tex` | stdlib | Header contact block, city, **date written by hand**, salutation and closing formula, French only |
| `blocks.py` | Factual CV blocks (experiences, projects) with alternative wordings that never add facts | imported by specs | none | All of it is personal data: becomes `profile.yaml` |
| `README_conventions.md` | Folder tree and naming convention | doc | none | Name in file pattern; contract and doc types; becomes `naming` in `config.yaml` |
| `CV_*.tex` (FR, EN) | Master CV sources | LaTeX | pdflatex, `geometry`, `titlesec`, `enumitem`, `hyperref`, `babel` | Personal content; the **layout** is reused for the anonymized Jinja2 template |

Shared traits worth keeping: one page, one column, standard section names, results with numbers, no em dash,
labels on one line, "never invent a fact" (alternative wordings only).

Example application (one complete case): `Offre_<Company>_<Role>.txt`, `ATS_<Company>_<Role>.txt`,
`CV_<First>_<Last>_<Company>_<Contract>_<Role>_<LANG>_<YYYY-MM>.{tex,pdf}`, and the matching `LM_...` pair in the
letters folder. The `spec.py` and `lm.txt` intermediates are not kept after generation: v2 keeps them in
`applications/<id>/` so a document can be regenerated. Observed letter structure: why this role, two or three
proofs taken from real experience, link with the company's projects, why work-study over an internship, close.
The old tracking CSV (`99_ARCHIVES`) has columns `Mois;Entreprise;Contrat;Poste;CV;LM;Statut / notes`: importable
in phase 10.

### Offer sources used today (from `import/veille-alternance.md`)

| Source | How it is queried today | Notes for `sources/` |
|---|---|---|
| LinkedIn public jobs | Built-in browser, no login; guest endpoints `/jobs-guest/jobs/api/seeMoreJobPostings/search` (params `keywords`, `geoId`, `f_TPR` freshness `r86400` = 24 h, `start`) and `/jobs-guest/jobs/api/jobPosting/<id>` for the description | Rate limited after about 20 calls, 1.5 s pause; keep titles matching `altern|apprenti|apprentice`; opt-in only |
| La bonne alternance | Fetch from the public site: `/api/v1/search` (`q`, `radius`, `latitude`, `longitude`, `hitsPerPage`, `mode=emplois`, `page`); response `hits`, date in `publication_date`, company in `organization_name`, detail link `/emploi/<sub_type>/<url_id>/x` | Ignore `sub_type=recruteurs_lba` (spontaneous applications, not offers); check whether the official API needs a token before phase 3 |
| Pasted text / URL | Offer text pasted in the chat | Becomes the `fiche-offre` skill |

Search keywords and coordinates are user settings (`config.yaml`), never defaults in the code.

## (b) Skills

### Used in practice today

| Practice | How it is done today | v2 skill |
|---|---|---|
| Offer watch | manual search, list in `veille-alternance.md` (to read) | `veille` |
| Fit check | `career-desk:job-fit` | `job-fit` (reprise, adds the /100 score from `scoring.py`) |
| CV tailoring | `career-desk:cv-tailor` + hand-written `spec.py` + `gen_cv.py` | `cv-adapter` |
| Cover letter | `career-desk:cover-letter` + `gen_lm.py` | `lettre-motivation` |
| ATS score | `ats_check.py` + `wrapcheck.py` | `ats-check` |
| Form filled together | browser, user handles accounts and sensitive fields | `formulaire-a-deux` |
| Tracking | CSV, then `career-desk:application-tracker` | `suivi-candidatures` |
| Interview prep | `career-desk:interview-prep` | `prep-entretien` |
| Offer comparison | `career-desk:offer-compare` | `comparer-offres` |
| CV review | `career-desk:cv-review` | folded into `cv-adapter` (review step) |

Installed plugins also relevant: a job-search plugin (search and tracker), `develop21-career-coach`, `docx`, `pdf`.
v2 does not depend on any of them: skills are rewritten inside the Kandid plugin so it works on a fresh install.

### Rules found in the user's workflow, to make generic

Watch (`veille` skill and `scoring.py`):

- Filter: real work-study contract (not internship or permanent job), target area, required level matches the
  user's degree, no school recruiting "for a partner" for another degree (flag for check), not already seen or applied.
- Score /100 on career goal, skills, studies and school/company rhythm, plus location; one line of justification and
  a list of points to check.
- When in doubt (contract type, intermediary, generic description), give the link to the user before preparing
  anything. Preparation starts only on the user's confirmation.

CV and letter (`profile.yaml` fields, defaults overridable):

| Rule observed | Generic field |
|---|---|
| Contact details on one full-width line under the name, then role title, then a subtitle with availability, duration and rhythm | `header.contact_line`, `header.subtitle` |
| Never write certain wordings (wrong degree name, "personal project", a city phrasing) | `rules.forbidden_terms` |
| Tools not practiced must never appear in the CV, and are stated frankly in the letter | `rules.unconfirmed_skills` |
| Tools actually used | `skills` with `confirmed: true` |
| A project still in progress is always labelled as such | `projects[].status: in_progress` |
| A default project is added first when fewer than 4 projects are chosen | `rules.default_project`, `rules.project_count` |
| Portfolio link preferred over the code host | `header.links` order |
| Only relevant programming languages | `cv-adapter` skill instruction |
| Associations and hobbies on two lines | template layout |
| Offer shorter than the wanted duration: the letter argues for the wanted duration | `rules.letter` |
| Degree lines with two sub-lines (prep class, then high-school diploma) | `education[].lines` |
| Certifications in progress listed on one line | `certifications[].status` |

Applications already sent with an old wording are not corrected afterwards: history is imported as is.

### Planned (from the brief)

`veille`, `job-fit`, `cv-adapter`, `lettre-motivation`, `ats-check`, `formulaire-a-deux`, `suivi-candidatures`,
`relances`, `prep-entretien`, `comparer-offres`, `bilan`, plus `setup` and `kandid-aide`.

### Proposed additions

| Skill | Why |
|---|---|
| `verif-honnetete` (agent `relecteur`) | The scripts rely on "never invent" by discipline only. An independent reviewer agent diffs skills and facts in the generated CV/LM against `profile.yaml` and blocks the "Prêt" status on any unknown claim |
| `fiche-offre` | Every application starts by saving the offer text (offers disappear). Used by `/postuler` and by the UI import |
| `import-cv` | Pre-fills `profile.yaml` from an existing `.tex`/`.docx`/`.pdf`, section by section (needed by `/setup`) |

## (c) Paths and naming conventions

| Item | Today | v2 |
|---|---|---|
| Master sources | master folder on a synced drive, never modified | `paths.master` in `config.yaml`; a hook blocks writes there |
| Application folder | `CV\<CONTRACT>\` and `LETTRES_MOTIVATION\<CONTRACT>\` | `paths.applications` + `naming.layout` (defaults reproduce today's tree) |
| File name | `TYPEDOC_<First>_<Last>_<Company>_<Contract>_<Role>_<LANG>_<YYYY-MM>.<ext>` | `naming.pattern` template, same default |
| Company | joined, no spaces or accents | slug function in `kandid_tools`, tested |
| Role | words joined by hyphens | same slug function |
| Contract | Alternance, Stage, Stage-PFE, CDI, Freelance | enum in `config.yaml` |
| Offer / ATS report | `Offre_<Company>_<Role>.txt`, `ATS_<Company>_<Role>.txt` next to the CV | same, plus `ats.json` in `applications/<id>/` for the UI |
| Working data | none (spec and body files deleted) | `<data>\applications\<id>\` (spec.yaml, letter.md, offer, reports) |
| Tracking | CSV in archives | `kandid.db` (SQLite) |
| User data folder | n/a | default `%USERPROFILE%\.kandid\`, outside the repo |

### History to migrate (phase 10, never committed)

| Source | Content | Volume | Target |
|---|---|---|---|
| `import/candidatures-workflow.md` | applications prepared or sent: date, company, role, score /100, short note (rhythm, distance, duration, reference number, platform) | about 17 | `application` rows with status `Prêt` or `Envoyée` |
| `import/veille-alternance.md` | offers seen per day: company, role, source id (LinkedIn id or LBA id), score or "discarded" with a reason | about 20 | `offer` rows used for deduplication |
| `99_ARCHIVES` CSV | older tracking | to count | `application` rows |

Also in the workflow file: a blocked contract (company froze apprenticeship contracts) to record as an event, not
as an application.
