# CV spec and letter

## `spec.yaml`

The CV is rendered from the profile; the spec only chooses and orders what goes in. Every id must exist in the profile.

```yaml
offer:
  company: <company>
  role: <role as written in the offer>
  url: <url, optional>
contract: <one of the contracts in config naming, e.g. Alternance, Stage, CDI>
lang: fr            # or en
title: <optional CV title, from the profile header or close to the offer's role>
experiences: [<experience id>, ...]          # rendered in this order: keep reverse chronological order
projects: [<project id>, {id: <id>, wording: <wording key>}, ...]
projects_title: <optional section title>
skills: [<skill group id>, ...]
```

- Pick the experiences and projects that prove the offer's requirements. Four projects by default
  (`rules.project_count`); with fewer, the profile's default project is added.
- Each experience and project has several wordings (`wordings` keys in the profile). Choose the one whose words match
  the offer best; `default` otherwise.
- Skill groups: those the offer cares about, most relevant first.
- One page is a hard limit: when the render overflows, drop the weakest project first.

## `letter.yaml`

```yaml
recipient:
  - <company>
  - <team or contact, if known>
  - <address lines, if known>
subject: <contract, role, and one useful fact such as the school programme or duration>
salutation: <optional, e.g. "Madame, Monsieur,">
body: |
  <paragraph 1>

  <paragraph 2>
closing: <optional closing formula>
```

- Three or four short paragraphs, under 300 words: why this company and role (from the offer, not generic praise);
  two or three facts from the profile that answer the main requirements; the practical side (rhythm, dates, duration)
  when it helps; an invitation to talk.
- Name a tool from `rules.unconfirmed_skills` only to say the user is learning it.
- Follow `rules.letter`.
- The date and the user's details are added by the template: do not write them.
