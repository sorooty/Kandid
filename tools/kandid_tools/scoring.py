"""Deterministic score /100 of an offer against the user's search and profile.

Domain neutral: every criterion comes from `config.yaml` or `profile.yaml`, none from a built-in
vocabulary. An unknown value gets half the points and a point to check, so a sparse offer is
neither hidden nor pushed to the top.
"""

import re
from datetime import datetime

from pydantic import BaseModel

from kandid_tools.ats import norm
from kandid_tools.config import WatchConfig
from kandid_tools.honesty import phrase_pattern
from kandid_tools.profile import Profile
from kandid_tools.sources.base import RawOffer

CONTRACT_POINTS = 25
KEYWORD_POINTS = 25
SKILL_POINTS = 25
AREA_POINTS = 15
FRESHNESS_POINTS = 10
# Matching this many profile skills earns every skill point.
SKILLS_FOR_FULL = 5
_FRESHNESS = ((7, 1.0), (14, 0.7), (31, 0.4))
_PARENTHESES = re.compile(r"\([^)]*\)")
_SEPARATORS = re.compile(r"[/,;]")


class Score(BaseModel):
    score: int
    justification: str
    points_to_check: list[str]


def profile_skills(profile: Profile) -> list[str]:
    """Skills the profile states, in order, without duplicates."""
    names = [item for group in profile.skills for item in group.items]
    names += [tech for project in profile.projects for tech in project.tech]
    return list(dict.fromkeys(names))


def _variants(term: str) -> list[str]:
    # "HTML/CSS" or "Excel (avancé)" never appear as such in an offer: look for each part.
    parts = _SEPARATORS.split(_PARENTHESES.sub(" ", term))
    return [part for part in parts if part.strip()] or [term]


def _found(terms: list[str], text: str) -> list[str]:
    return [t for t in terms if any(phrase_pattern(v).search(text) for v in _variants(t))]


def score(
    offer: RawOffer,
    watch: WatchConfig,
    skills: list[str],
    *,
    in_area: bool | None,
    today: datetime,
) -> Score:
    """`in_area` is None when the offer's location is unknown; `today` must be timezone aware."""
    title, body = norm(offer.title), norm(offer.description)
    reasons: list[str] = []
    checks: list[str] = []
    total = 0.0

    if offer.contract is None:
        total += CONTRACT_POINTS / 2
        checks.append("type de contrat non précisé")
    elif not watch.contracts or offer.contract in watch.contracts:
        total += CONTRACT_POINTS
        reasons.append(f"contrat {offer.contract.value}")

    in_title = _found(watch.keywords, title)
    in_body = _found(watch.keywords, body)
    if not watch.keywords or in_title:
        total += KEYWORD_POINTS
        if in_title:
            reasons.append(f"titre : {', '.join(in_title[:3])}")
    elif in_body:
        total += KEYWORD_POINTS * 0.6
        reasons.append(f"description : {', '.join(in_body[:3])}")

    matched = _found(skills, f"{title}\n{body}")
    total += SKILL_POINTS * min(len(matched), SKILLS_FOR_FULL) / SKILLS_FOR_FULL
    if matched:
        reasons.append(f"compétences : {', '.join(matched[:5])}")

    if in_area is None:
        total += AREA_POINTS / 2
        checks.append("lieu non précisé")
    elif in_area:
        total += AREA_POINTS
        reasons.append("dans la zone")

    if offer.published_at is None:
        total += FRESHNESS_POINTS / 2
    else:
        age = (today - offer.published_at).days
        ratio = next((r for days, r in _FRESHNESS if age <= days), 0.0)
        total += FRESHNESS_POINTS * ratio
        reasons.append(f"publiée il y a {max(age, 0)} j")

    if offer.intermediary:
        checks.append("publiée par une école ou un intermédiaire")
    if not offer.description:
        checks.append("description absente : lire l'offre sur le site")
    return Score(
        score=round(total),
        justification=" ; ".join(reasons) or "aucun critère ne correspond",
        points_to_check=checks,
    )
