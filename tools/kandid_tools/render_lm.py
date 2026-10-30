"""Cover letter `.tex` from a profile and a `letter.yaml`, dated on the day it is rendered."""

import re
from datetime import date
from pathlib import Path

from pydantic import Field

from kandid_tools.files import load_yaml
from kandid_tools.latex import environment
from kandid_tools.profile import Lang, Profile, Strict

_MONTHS = {
    Lang.FR: [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ],
    Lang.EN: [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ],
}  # fmt: skip

_DEFAULTS = {
    Lang.FR: {
        "babel": "french",
        "subject": "Objet :",
        "salutation": "Madame, Monsieur,",
        "closing": "Je vous prie d'agréer, Madame, Monsieur, l'expression de mes salutations "
        "distinguées.",
    },
    Lang.EN: {
        "babel": "english",
        "subject": "Subject:",
        "salutation": "Dear Hiring Manager,",
        "closing": "Yours sincerely,",
    },
}


class Letter(Strict):
    recipient: list[str] = Field(min_length=1)
    subject: str
    # Paragraphs separated by a blank line.
    body: str
    salutation: str | None = None
    closing: str | None = None


def load_letter(path: Path) -> Letter:
    return Letter.model_validate(load_yaml(path))


def letter_date(day: date, lang: Lang, city: str) -> str:
    month = _MONTHS[lang][day.month - 1]
    if lang is Lang.FR:
        first = "1er" if day.day == 1 else str(day.day)
        return f"{city}, le {first} {month} {day.year}"
    return f"{city}, {month} {day.day}, {day.year}"


def render_lm(profile: Profile, letter: Letter, lang: Lang, day: date) -> str:
    texts = _DEFAULTS[lang]
    context = {
        "babel": texts["babel"],
        "identity": profile.identity,
        "recipient": letter.recipient,
        "date": letter_date(day, lang, profile.identity.city),
        "subject_label": texts["subject"],
        "subject": letter.subject,
        "salutation": letter.salutation or texts["salutation"],
        "paragraphs": [p.strip() for p in re.split(r"\n\s*\n", letter.body) if p.strip()],
        "closing": letter.closing or texts["closing"],
    }
    return environment().get_template("lm.tex.j2").render(context)
