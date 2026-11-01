# Building profile.yaml from an existing CV

The profile is the only source of every CV and letter Kandid writes. It must say what the CV says, nothing more.

## Extract

`kandid importer "<cv file>"` returns the CV's text cut into sections (`.tex`, `.pdf` or `.docx`). It only reads the
file. If the user has no CV, start from empty sections and ask for each one.

## Map, section by section

Use the structure of the fictional example profile whose path SKILL.md gives (read it for the shape only, none of
its content). For each section below, show the user what you extracted in plain text, ask them to
confirm or correct (AskUserQuestion: "C'est juste" first, then "À corriger"), and only then keep it:

1. `identity`: names, email, phone (optional), city, links. Ask before keeping a phone number or an address line;
   never keep a full postal address, a date of birth or a social security number.
2. `header` (title and availability subtitle) and `summary`. Rewrite only for grammar; keep the user's claims.
3. `education`: school, location, dates, lines.
4. `experiences`: one entry per job, an `id` in lowercase (`lumio`, `stage-2025`), role, company, dates and a
   `default` wording with one bullet per fact of the CV. Bold (`**...**`) the tools and figures that are in the CV.
5. `projects`: same, with `tech` listing only tools the CV names for that project; `status: in_progress` if the CV
   says so.
6. `skills`: groups with an `id`, a label and the items as written in the CV.
7. `certifications`, `languages`, `soft_skills`, `associations`, `hobbies` when present.
8. `rules`: ask which tools they are learning but have not practiced (`unconfirmed_skills`), words they never want to
   see (`forbidden_terms`), and any standing instruction for letters (`letter`).

Rules:
- Never add a skill, tool, figure, date or responsibility the CV does not state. If something is ambiguous (a tool in
  a list but no experience using it), ask.
- Dates: check that past experiences have ended before today; flag any inconsistency to the user.
- Texts can be one string or `{fr: ..., en: ...}`. Add the second language only if the user wants documents in both,
  and translate faithfully; show the translation for validation.
- Do not log, quote back in full, or send the CV anywhere other than this conversation.
