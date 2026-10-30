"""Adzuna job search API (free app id and key). Docs: https://developer.adzuna.com/docs/search.

Descriptions are snippets, and titles may carry highlight tags: both are reduced to plain text.
"""

import httpx
from pydantic import Field

from kandid_tools.config import ContractKind, WatchConfig
from kandid_tools.sources.base import (
    UNKNOWN_COMPANY,
    MissingCriteria,
    Payload,
    RawOffer,
    SourceError,
    classify_contract,
    html_to_text,
    json_body,
    parse_datetime,
    request,
)

NAME = "adzuna"
URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"
RESULTS_PER_PAGE = 50
_CONTRACTS = {"permanent": ContractKind.PERMANENT, "contract": ContractKind.FIXED_TERM}


class _Named(Payload):
    display_name: str | None = None


class _Job(Payload):
    # Documented as a string; accept a number too rather than lose the offer.
    id: str | int
    title: str
    description: str = ""
    created: str | None = None
    redirect_url: str | None = None
    company: _Named = _Named()
    location: _Named = _Named()
    contract_type: str | None = None


class _Response(Payload):
    results: list[_Job] = Field(default_factory=list)


def covers_area(watch: WatchConfig) -> bool:
    return bool(watch.area.city)


def _contract(job: _Job) -> ContractKind | None:
    # The title says more than `contract_type`: an apprenticeship is often typed "contract".
    return classify_contract(job.title) or _CONTRACTS.get(job.contract_type or "")


def search(client: httpx.Client, watch: WatchConfig, secrets: dict[str, str]) -> list[RawOffer]:
    if not watch.keywords:
        raise MissingCriteria("aucun mot-clé dans watch.keywords : Adzuna cherche par mots-clés")
    offers: dict[str, RawOffer] = {}
    # One call per keyword: `what` requires every word, and keywords are alternatives.
    for keyword in watch.keywords:
        params: dict[str, str | int] = {
            "app_id": secrets["app_id"],
            "app_key": secrets["app_key"],
            "what": keyword,
            "max_days_old": watch.max_age_days,
            "results_per_page": RESULTS_PER_PAGE,
        }
        if watch.area.city:
            params |= {"where": watch.area.city, "distance": watch.area.radius_km}
        response = request(client, "GET", URL.format(country=watch.country), params=params)
        try:
            payload = _Response.model_validate(json_body(response))
        except ValueError:
            raise SourceError("réponse inattendue d'Adzuna") from None
        for job in payload.results:
            offers[str(job.id)] = RawOffer(
                source=NAME,
                external_id=str(job.id),
                company=job.company.display_name or UNKNOWN_COMPANY,
                title=html_to_text(job.title),
                location=job.location.display_name,
                contract=_contract(job),
                url=job.redirect_url,
                description=html_to_text(job.description),
                published_at=parse_datetime(job.created),
            )
    return list(offers.values())
