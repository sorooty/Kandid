"""Local, deterministic ATS heuristic.

Format score /100 = parsing (40) + structure (30) + content (30). With an offer, the global score
is 50% format and 50% offer keywords found word for word. The rules follow what public ATS
documentation says (Workday, Taleo, Greenhouse, Lever): extractable text, one column, standard
sections, readable contact and dates. It compares versions of a CV; it does not predict a real ATS.
"""

import itertools
import re
import unicodedata
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel

from kandid_tools import pdftools


class Level(StrEnum):
    OK = "OK"
    KO = "KO"
    INFO = "INFO"


class Check(BaseModel):
    level: Level
    message: str


class Keywords(BaseModel):
    score: int
    found: list[str]
    missing: list[str]


class AtsReport(BaseModel):
    parsing: int
    structure: int
    content: int
    format_score: int
    checks: list[Check]
    keywords: Keywords | None = None
    global_score: int


def norm(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


_SECTIONS = {
    "formation": ["formation", "education", "parcours academique"],
    "experience": ["experience", "experiences professionnelles", "professional experience"],
    "competences": ["competences", "skills", "technical skills"],
    "projets": ["projets", "projects"],
    "langues": ["langues", "languages"],
    "certifications": ["certifications", "certificates"],
}
_CORE_SECTIONS = ("formation", "experience", "competences")

_STOP = set(
    norm(
        """a au aux avec ce ces dans de des du en et for from in la le les leur
of on or ou par pour sur the to un une vos votre we you your nous are is be will with
as at by an h f x poste mission missions profil vous etes ainsi tout tous toute
plus tres bien etre avoir faire sein afin equipe equipes qui que quoi dont est sont
chaque deja aupres lien entre leur leurs nos notre cette cet comme mais
stage alternance alternant apprentissage contrat ecole diplome https www
identifier concevoir outils outil besoin besoins cas usage usages our this that can
role team job work offer"""
    ).split()
)

_MONTH_END = re.compile(
    r"\d{4}\s*$|(janv|fevr|mars|avril|mai|juin|juil|aout|sept|oct|nov|dec|present|jan|feb"
    r"|apr|may|jun|jul|aug|sep)\w*\.?\s*\d{0,4}\s*$"
)
_RESULT = re.compile(
    r"\d+\s?%|\+\s?\d+|\d+\s(?:clients|heures|hours|referentiels|modules|variables|mois|months"
    r"|utilisateurs|users|projets|projects)"
)


def _stem(word: str) -> str:
    if len(word) <= 4:
        return word
    return re.sub(r"e$", "", re.sub(r"[sx]$", "", word))


def format_checks(
    raw: str, layout: str, fonts: str, pages: int, cities: Sequence[str]
) -> tuple[dict[str, int], list[Check]]:
    points = {"parsing": 0, "structure": 0, "content": 0}
    checks: list[Check] = []

    def add(ok: bool, message: str) -> None:
        checks.append(Check(level=Level.OK if ok else Level.KO, message=message))

    n = norm(raw)
    words = re.findall(r"\w+", raw)

    # Parsing (40)
    if len(words) > 250:
        points["parsing"] += 12
    add(len(words) > 250, f"Texte extractible ({len(words)} mots)")
    font_lines = fonts.splitlines()[2:]
    type3 = sum("Type 3" in line for line in font_lines)
    no_unicode = sum(line.split()[-3:-2] == ["no"] for line in font_lines)
    if type3 == 0 and no_unicode == 0:
        points["parsing"] += 8
    add(
        type3 == 0 and no_unicode == 0,
        f"Polices : {type3} de type 3, {no_unicode} sans table Unicode",
    )
    corrupted = raw.count("�")
    if corrupted == 0:
        points["parsing"] += 6
    add(corrupted == 0, f"{corrupted} caractère(s) corrompu(s)")
    # A two-column layout shows as lines with two blocks far apart, dates at the end excepted.
    lines = [line for line in layout.splitlines() if line.strip()]
    gaps = [
        line
        for line in lines
        if re.search(r"\S {6,}\S", line.strip()) and not _MONTH_END.search(norm(line.strip()))
    ]
    ratio = len(gaps) / max(len(lines), 1)
    if ratio < 0.08:
        points["parsing"] += 10
    elif ratio < 0.25:
        points["parsing"] += 3
    add(ratio < 0.08, f"Mise en page une colonne ({ratio:.0%} de lignes suspectes)")
    # A header in plain text (not an image) shows the email among the first characters.
    if re.search(r"[\w.+-]+@[\w-]+\.\w+", raw[:400]):
        points["parsing"] += 4

    # Structure (30)
    found = [k for k, v in _SECTIONS.items() if any(re.search(rf"^\s*{x}", n, re.M) for x in v)]
    core = [k for k in _CORE_SECTIONS if k in found]
    points["structure"] += 5 * len(core) + 2 * min(len(found) - len(core), 3)
    add(len(core) == len(_CORE_SECTIONS), f"Sections standard : {', '.join(found) or 'aucune'}")
    contact = {
        "email": bool(re.search(r"[\w.+-]+@[\w-]+\.\w+", raw)),
        "téléphone": bool(re.search(r"(\+\d{2,3}\s?|0)[1-9]([\s.]?\d{2}){4}", raw)),
        "linkedin": "linkedin.com/in/" in n,
        "localisation": any(norm(city) in n[:600] for city in cities),
    }
    points["structure"] += 2 * sum(contact.values())
    missing = [k for k, v in contact.items() if not v]
    add(not missing, "Contact : " + ("complet" if not missing else "manque " + ", ".join(missing)))
    if pages == 1:
        points["structure"] += 1
        add(True, "1 page")
    else:
        checks.append(Check(level=Level.INFO, message=f"{pages} pages (1 page conseillée)"))

    # Content (30)
    years = re.findall(r"(?:19|20)\d{2}", raw)
    points["content"] += 8 if len(years) >= 6 else 3
    add(len(years) >= 6, f"Dates lisibles ({len(years)} années)")
    results = _RESULT.findall(n)
    points["content"] += 2 * min(len(results), 6)
    add(len(results) >= 4, f"{len(results)} résultat(s) chiffré(s)")
    if 350 <= len(words) <= 800:
        points["content"] += 6
    else:
        points["content"] += 2
    add(350 <= len(words) <= 800, f"Longueur : {len(words)} mots (cible 350 à 800)")
    if re.search(r"altern|apprenti|stage|intern|work-study", n[:700]):
        points["content"] += 4
    return points, checks


def offer_keywords(offer: str, cv_text: str, company: str | None = None) -> Keywords:
    """Most frequent offer terms and word pairs, plurals folded, URLs and company name left out."""
    company_words = set(norm(company).split()) if company else set()
    body = "\n".join(line for line in offer.splitlines() if not re.match(r"\s*https?://", line))
    jd = norm(body).replace("-", " ")
    cv = " ".join(_stem(w) for w in re.findall(r"[a-z0-9+#.]+", norm(cv_text).replace("-", " ")))
    tokens = [
        t
        for t in re.findall(r"[a-z0-9][a-z0-9+#.]*[a-z0-9+#]", jd)
        if t not in _STOP and t not in company_words and len(t) > 2 and not t.isdigit()
    ]
    frequency: dict[str, float] = {}
    for token in tokens:
        frequency[_stem(token)] = frequency.get(_stem(token), 0) + 1
    words = [None if w in _STOP else _stem(w) for w in re.findall(r"[a-z0-9+#.]+", jd)]
    for a, b in itertools.pairwise(words):
        if a and b and len(a) > 2 and len(b) > 2:
            frequency[f"{a} {b}"] = frequency.get(f"{a} {b}", 0) + 1.5
    top = [k for k in sorted(frequency, key=lambda k: -frequency[k]) if frequency[k] >= 2][:30]
    found = [k for k in top if re.search(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", cv)]
    return Keywords(
        score=round(100 * len(found) / max(len(top), 1)),
        found=found,
        missing=[k for k in top if k not in found],
    )


def analyze(
    pdf: Path, offer: str | None = None, *, company: str | None = None, cities: Sequence[str] = ()
) -> AtsReport:
    raw = pdftools.text(pdf)
    points, checks = format_checks(
        raw,
        pdftools.text(pdf, layout=True),
        pdftools.fonts(pdf),
        pdftools.page_count(pdf),
        cities,
    )
    format_score = sum(points.values())
    keywords = offer_keywords(offer, raw, company) if offer else None
    global_score = format_score if keywords is None else round((format_score + keywords.score) / 2)
    return AtsReport(
        parsing=points["parsing"],
        structure=points["structure"],
        content=points["content"],
        format_score=format_score,
        checks=checks,
        keywords=keywords,
        global_score=global_score,
    )


def to_text(report: AtsReport) -> str:
    lines = [
        f"FORMAT ATS : {report.format_score}/100 (parsing {report.parsing}/40, "
        f"structure {report.structure}/30, contenu {report.content}/30)",
        *(f"  [{c.level}] {c.message}" for c in report.checks),
    ]
    if report.keywords is not None:
        kw = report.keywords
        total = len(kw.found) + len(kw.missing)
        lines += [
            f"MOTS-CLÉS DE L'OFFRE : {kw.score}/100 ({len(kw.found)}/{total})",
            "  Présents : " + ", ".join(kw.found),
            "  Manquants : " + ", ".join(kw.missing),
            f"SCORE GLOBAL : {report.global_score}/100",
        ]
    return "\n".join(lines)
