"""La bonne alternance, through the API Apprentissage (free account, Bearer token).

Spec: https://api.apprentissage.beta.gouv.fr/api/documentation/json, operation `jobSearch`.
Searches by ROME job codes and area; at most 150 offers per underlying source.
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
    html_to_text,
    json_body,
    parse_datetime,
    request,
)

NAME = "labonnealternance"
URL = "https://api.apprentissage.beta.gouv.fr/api/job/v1/search"


class _Identifier(Payload):
    id: str | None = None
    partner_job_id: str
    partner_label: str


class _Location(Payload):
    address: str | None = None


class _Workplace(Payload):
    name: str | None = None
    brand: str | None = None
    legal_name: str | None = None
    location: _Location = _Location()


class _Apply(Payload):
    url: str | None = None


class _Publication(Payload):
    creation: str | None = None


class _OfferBody(Payload):
    title: str
    description: str = ""
    publication: _Publication = _Publication()


class _Job(Payload):
    identifier: _Identifier
    workplace: _Workplace = _Workplace()
    apply: _Apply = _Apply()
    offer: _OfferBody
    # True when a training school posted the offer on behalf of a company.
    is_delegated: bool = False


class _Response(Payload):
    # Only `jobs` holds offers: `recruiters` are companies likely to hire, not open positions.
    jobs: list[_Job] = Field(default_factory=list)


def _company(workplace: _Workplace) -> str:
    return workplace.brand or workplace.name or workplace.legal_name or UNKNOWN_COMPANY


def covers_area(watch: WatchConfig) -> bool:
    """The search itself is bounded by the area: its results need no location check."""
    area = watch.area
    return (area.latitude is not None and area.longitude is not None) or bool(area.departements)


def _params(watch: WatchConfig) -> dict[str, str | list[str] | float]:
    params: dict[str, str | list[str] | float] = {"romes": ",".join(watch.romes)}
    area = watch.area
    if area.latitude is not None and area.longitude is not None:
        # Two decimals (about 1 km): enough for the search, without sending the exact address.
        lat, lon = round(area.latitude, 2), round(area.longitude, 2)
        params |= {"latitude": lat, "longitude": lon, "radius": area.radius_km}
    if area.departements:
        params["departements"] = area.departements
    return params


def search(client: httpx.Client, watch: WatchConfig, secrets: dict[str, str]) -> list[RawOffer]:
    if not watch.romes:
        raise MissingCriteria(
            "aucun code ROME dans watch.romes : cette source ne cherche que par métier"
        )
    response = request(
        client,
        "GET",
        URL,
        params=_params(watch),
        headers={"Authorization": f"Bearer {secrets['token']}"},
    )
    try:
        payload = _Response.model_validate(json_body(response))
    except ValueError:
        raise SourceError("réponse inattendue de La bonne alternance") from None
    return [
        RawOffer(
            source=NAME,
            external_id=f"{job.identifier.partner_label}:{job.identifier.partner_job_id}",
            company=_company(job.workplace),
            title=job.offer.title,
            location=job.workplace.location.address,
            contract=ContractKind.WORK_STUDY,
            url=job.apply.url,
            description=html_to_text(job.offer.description),
            published_at=parse_datetime(job.offer.publication.creation),
            intermediary=job.is_delegated,
        )
        for job in payload.jobs
    ]
