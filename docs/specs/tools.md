# Spec: Python tools and anonymized CV template

## Problem

The author's CV workflow runs on personal scripts (`gen_cv.py`, `gen_lm.py`, `ats_check.py`, `wrapcheck.py`,
`blocks.py`) full of hard-coded personal data, with an executable `spec.py` per offer and a letter date typed by
hand (see `docs/INVENTAIRE.md` section (a)). Nothing is reusable by another student, nothing is tested, and "never
invent a fact" relies on discipline only. Every later phase (database, plugin skills, app) needs this logic as a
tested library with a deterministic CLI.

## User story

As a student, I describe myself once in `profile.yaml` and, for each offer, a small `spec.yaml` that picks and words
my real experiences. `kandid` renders a one-page CV and a dated cover letter as PDF, names and files them by my
convention, scores them for ATS, and refuses any skill or tool that is not in my profile.

## Scope

In:

- `tools/kandid_tools` package and `kandid` CLI (typer), each command with a `--json` output for skills and the app.
- `profile.py`: pydantic schema of `profile.yaml` (header, education, experiences and projects with alternative
  wordings, skill groups whose items all count as practiced, certifications, languages, hobbies, `rules`:
  `forbidden_terms`, `unconfirmed_skills`, `default_project`, `project_count`, letter rules). Any text can be a
  single string or given per language (`fr`, `en`).
- `spec.py`: pydantic schema of the per-offer `spec.yaml` (offer reference, contract, language, chosen items and
  wording keys, title and subtitle). Pure data, never executed.
- `naming.py`: company and role slugs, configurable file pattern (default
  `TYPEDOC_<First>_<Last>_<Company>_<Contract>_<Role>_<LANG>_<YYYY-MM>`) and folder layout
  (`CV/<CONTRACT>`, `LETTRES_MOTIVATION/<CONTRACT>`).
- `status.py`: the 9 Kanban columns (À voir, À préparer, Prêt, Envoyée, Relance, Entretien, Offre, Refus, Archivée)
  and their transitions, porting the v1 rules and tests (reopen after silence or refusal, repeated interviews).
- `ats.py` and `wrapcheck.py`: ports of the scripts, JSON and text output. Section titles come from the template
  labels, the city from the profile.
- `render_cv.py`, `render_lm.py`: Jinja2 with LaTeX-safe delimiters, LaTeX escaping of every field, pdflatex
  through `subprocess` with an argument list; automatic localized letter date; default project prepended when fewer
  than `project_count` projects are chosen.
- `honesty.py`: lists skills and tools cited in a rendered `.tex`, PDF or letter and flags any absent from the
  profile, unconfirmed, or matching `forbidden_terms`. With `--letter`, an unconfirmed tool is reported but does not
  block, since the letter may say frankly it is not practiced yet.
- `kandid_tools/templates/cv.tex.j2` and `lm.tex.j2`, shipped with the package, layout derived from the master CV,
  no personal data. One template per document, section titles per language in `render_cv.LABELS`. The letter text
  comes from a `letter.yaml` (recipient lines, subject, body, optional salutation and closing).
- `examples/`: profile "Camille Martin", 3 fictional offers with their `spec.yaml`, one `letter.yaml`. Rendered
  PDFs are not committed: tests regenerate them.

Out: SQLite and offer sources (phase 3), skills, commands and hooks (phase 4), `config.yaml` generation by `/setup`
(phase 5, here a minimal schema with defaults), scoring /100 for job fit (phase 3 with the watch), `.docx` output.

## Acceptance criteria

- `uv run pytest` and `pnpm check` green; every module has unit tests, renders are tested when pdflatex is present
  and skipped otherwise.
- Camille's CV renders to exactly 1 page (`pdfinfo`) in FR and EN, and `kandid wrapcheck` reports no wrapped label.
- PNG captures of the template PDF and Camille's PDF are compared side by side (artifact for the PR).
- `kandid honesty` fails on a document that cites a tool missing from the profile, or listed in
  `unconfirmed_skills` (in `--letter` mode the latter is reported for review without blocking). `kandid render`
  runs the same check and refuses to write a document that fails it.
- A `spec.yaml` referencing an unknown experience or wording key is rejected with a clear message.
- No personal data in the repository: fixtures are fictional only.

## Data touched

Reads `profile.yaml`, `spec.yaml`, offer text and generated PDFs from paths given on the command line; writes `.tex`,
`.pdf` and reports to an output folder given on the command line. No database, no network, nothing sent to Claude.
The master CV folder is read once by hand to derive the layout, never by the code.

## Decisions

1. Layout derived from the master CV (read once, by hand). Latin Modern fonts and `glyphtounicode` added so ATS
   parsers read ligatures such as "fi" as letters.
2. YAML parser: PyYAML with `safe_load`.
3. Honesty vocabulary: `unconfirmed_skills` plus a bundled list of tech terms (`kandid_tools/data/tech_terms.txt`).
   A term is accepted when it appears anywhere in the profile facts. Ambiguous words (Tableau, Go, R) stay out.
4. Status transitions: À voir to À préparer; À préparer to Prêt; Prêt to Envoyée or back to À préparer; then the
   previous rules (Relance replaces followed_up, Refus replaces rejected, no_response is dropped since a silence is
   visible from dates). Any column can be archived, and archiving is final.
