"""Checks that a generated CV or letter claims no tool or skill the profile does not back."""

import re
from enum import StrEnum
from functools import cache
from importlib.resources import files
from pathlib import Path

from pydantic import BaseModel

from kandid_tools import pdftools
from kandid_tools.ats import norm
from kandid_tools.files import read_text
from kandid_tools.profile import Profile


class IssueKind(StrEnum):
    UNKNOWN = "unknown"
    UNCONFIRMED = "unconfirmed"
    FORBIDDEN = "forbidden"


class Issue(BaseModel):
    term: str
    kind: IssueKind
    blocking: bool


class HonestyReport(BaseModel):
    ok: bool
    issues: list[Issue]


_MESSAGES = {
    IssueKind.UNKNOWN: "absent du profil",
    IssueKind.UNCONFIRMED: "outil non pratiqué (unconfirmed_skills)",
    IssueKind.FORBIDDEN: "formulation interdite (forbidden_terms)",
}

_TEX_UNESCAPES = {
    r"\&": "&",
    r"\#": "#",
    r"\%": "%",
    r"\_": "_",
    r"\$": "$",
    "{[}": "[",
    "{]}": "]",
    "{*}": "*",
}
# In tech_terms.txt, "=Swift" means the case must match: "swift" or "excel" are ordinary words.
_EXACT_CASE = "="


@cache
def tech_terms() -> tuple[tuple[str, bool], ...]:
    """(term, case_sensitive) pairs."""
    content = files("kandid_tools").joinpath("data", "tech_terms.txt").read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines()]
    return tuple(
        (line.removeprefix(_EXACT_CASE), line.startswith(_EXACT_CASE))
        for line in lines
        if line and not line.startswith("#")
    )


def _term_pattern(term: str, *, case_sensitive: bool = False) -> re.Pattern[str]:
    # Symbols count as part of a name: "C" must not match inside "C++", nor "Java" in "JavaScript".
    # "Power BI" and "PowerBI" are the same tool, and a PDF line break may split a name.
    body = r"\s*".join(re.escape(word) for word in term.split())
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(rf"(?<![\w+#.]){body}(?![\w+#])", flags)


def untex(content: str) -> str:
    for escaped, plain in _TEX_UNESCAPES.items():
        content = content.replace(escaped, plain)
    return content


def read_document(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return pdftools.text(path)
    content = read_text(path)
    return untex(content) if path.suffix.lower() == ".tex" else content


def _forbidden_pattern(term: str) -> re.Pattern[str]:
    body = r"\s+".join(re.escape(word) for word in norm(term).split())
    return re.compile(rf"(?<!\w){body}(?!\w)")


def check_text(text: str, profile: Profile, *, letter: bool = False) -> HonestyReport:
    """Only known names are spotted: the bundled tech terms and `unconfirmed_skills`. A tool
    outside both lists goes unnoticed.

    In a letter, an unconfirmed tool may be named to say frankly it is not practiced yet: it is
    reported for review but does not block. In a CV it always blocks."""
    facts = "\n".join(profile.fact_texts())
    unconfirmed = {t.lower() for t in profile.rules.unconfirmed_skills}
    issues: list[Issue] = []
    seen: set[str] = set()
    candidates = [(t, False) for t in profile.rules.unconfirmed_skills] + list(tech_terms())
    for term, case_sensitive in candidates:
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        if key in unconfirmed:
            if _term_pattern(term).search(text):
                issues.append(Issue(term=term, kind=IssueKind.UNCONFIRMED, blocking=not letter))
            continue
        pattern = _term_pattern(term, case_sensitive=case_sensitive)
        if pattern.search(text) and not pattern.search(facts):
            issues.append(Issue(term=term, kind=IssueKind.UNKNOWN, blocking=True))
    normalized = norm(text)
    issues.extend(
        Issue(term=term, kind=IssueKind.FORBIDDEN, blocking=True)
        for term in profile.rules.forbidden_terms
        if _forbidden_pattern(term).search(normalized)
    )
    return HonestyReport(ok=not any(i.blocking for i in issues), issues=issues)


def to_text(report: HonestyReport) -> str:
    if not report.issues:
        return "OK : aucun outil ni compétence hors profil"
    lines = ["BLOQUANT" if not report.ok else "À RELIRE"]
    lines += [
        f"  [{'KO' if i.blocking else 'INFO'}] {i.term} : {_MESSAGES[i.kind]}"
        for i in report.issues
    ]
    return "\n".join(lines)
