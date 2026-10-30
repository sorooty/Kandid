"""Spot the same offer published on several sources."""

import re

from kandid_tools.ats import norm

# Legal forms and gender markers differ from one board to the next for the same offer.
_LEGAL_FORMS = re.compile(
    r"\b(sa|sas|sasu|sarl|eurl|sca|scop|gmbh|ag|ltd|limited|inc|llc|plc|bv)\b"
)
_GENDER = re.compile(r"\b[hfmx](\s*/\s*[hfmx])+\b")
_NON_WORD = re.compile(r"[^a-z0-9]+")


def _clean(text: str) -> str:
    return " ".join(_NON_WORD.sub(" ", text).split())


def fingerprint(company: str, title: str) -> str:
    company_key = _clean(_LEGAL_FORMS.sub(" ", _clean(norm(company))))
    title_key = _clean(_GENDER.sub(" ", norm(title)))
    return f"{company_key}|{title_key}"
