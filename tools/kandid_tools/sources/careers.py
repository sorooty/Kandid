"""Career pages of the companies the user follows, through their ATS public job APIs.

No key needed: these endpoints serve what the company publishes on its own careers site.
- Greenhouse: https://docs.greenhouse.io/job-board.html
- Lever: https://github.com/lever/postings-api
- Ashby: https://developers.ashbyhq.com/docs/public-job-posting-api
- SmartRecruiters: GET /v1/companies/{id}/postings (descriptions need one call per offer, so
  the title alone is kept)
- Recruitee: GET https://{company}.recruitee.com/api/offers/
"""

import re
from collections.abc import Callable

import httpx
from pydantic import Field

from kandid_tools.ats import norm
from kandid_tools.config import Ats, Company, ContractKind, WatchConfig
from kandid_tools.honesty import phrase_pattern
from kandid_tools.sources.base import (
    MissingCriteria,
    PartialResult,
    Payload,
    RawOffer,
    SourceError,
    classify_contract,
    html_to_text,
    json_body,
    parse_datetime,
    request,
)

NAME = "careers"
SMARTRECRUITERS_PAGE = 100


def _get(client: httpx.Client, url: str, **params: str | int) -> object:
    return json_body(request(client, "GET", url, params=params))


# Greenhouse ---------------------------------------------------------------------------------


class _GhLocation(Payload):
    name: str | None = None


class _GhJob(Payload):
    id: int
    title: str
    updated_at: str | None = None
    absolute_url: str | None = None
    location: _GhLocation = _GhLocation()
    content: str | None = None


class _GhResponse(Payload):
    jobs: list[_GhJob] = Field(default_factory=list)


def _greenhouse(client: httpx.Client, company: Company) -> list[RawOffer]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{company.board}/jobs"
    payload = _GhResponse.model_validate(_get(client, url, content="true"))
    return [
        RawOffer(
            source=NAME,
            external_id=f"greenhouse:{company.board}:{job.id}",
            company=company.name,
            title=job.title,
            location=job.location.name,
            contract=classify_contract(job.title),
            url=job.absolute_url,
            description=html_to_text(job.content),
            published_at=parse_datetime(job.updated_at),
        )
        for job in payload.jobs
    ]


# Lever --------------------------------------------------------------------------------------


class _LeverCategories(Payload):
    location: str | None = None
    commitment: str | None = None


class _LeverPosting(Payload):
    id: str
    text: str
    hostedUrl: str | None = None
    descriptionPlain: str = ""
    createdAt: int | None = None
    workplaceType: str | None = None
    categories: _LeverCategories = _LeverCategories()


def _lever(client: httpx.Client, company: Company) -> list[RawOffer]:
    url = f"https://api.lever.co/v0/postings/{company.board}"
    raw = _get(client, url, mode="json")
    if not isinstance(raw, list):
        raise ValueError("liste attendue")
    postings = [_LeverPosting.model_validate(item) for item in raw]
    return [
        RawOffer(
            source=NAME,
            external_id=f"lever:{company.board}:{p.id}",
            company=company.name,
            title=p.text,
            location=p.categories.location,
            contract=classify_contract(p.categories.commitment, p.text),
            remote=p.workplaceType == "remote" if p.workplaceType else None,
            url=p.hostedUrl,
            description=p.descriptionPlain,
            published_at=parse_datetime(p.createdAt),
        )
        for p in postings
    ]


# Ashby --------------------------------------------------------------------------------------

_ASHBY_TYPES = {"Intern": ContractKind.INTERNSHIP, "Contract": ContractKind.FREELANCE}


class _AshbyJob(Payload):
    id: str | None = None
    title: str
    location: str | None = None
    employmentType: str | None = None
    publishedAt: str | None = None
    jobUrl: str
    descriptionPlain: str = ""
    isRemote: bool | None = None


class _AshbyResponse(Payload):
    jobs: list[_AshbyJob] = Field(default_factory=list)


def _ashby(client: httpx.Client, company: Company) -> list[RawOffer]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{company.board}"
    payload = _AshbyResponse.model_validate(_get(client, url))
    return [
        RawOffer(
            source=NAME,
            # The documentation does not promise an id; the job URL is stable.
            external_id=f"ashby:{company.board}:{job.id or job.jobUrl}",
            company=company.name,
            title=job.title,
            location=job.location,
            contract=classify_contract(job.title) or _ASHBY_TYPES.get(job.employmentType or ""),
            remote=job.isRemote,
            url=job.jobUrl,
            description=job.descriptionPlain,
            published_at=parse_datetime(job.publishedAt),
        )
        for job in payload.jobs
    ]


# SmartRecruiters ----------------------------------------------------------------------------


class _SrLocation(Payload):
    fullLocation: str | None = None
    city: str | None = None
    remote: bool | None = None


class _SrType(Payload):
    id: str | None = None
    label: str | None = None


class _SrPosting(Payload):
    id: str
    name: str
    releasedDate: str | None = None
    location: _SrLocation = _SrLocation()
    typeOfEmployment: _SrType = _SrType()


class _SrResponse(Payload):
    content: list[_SrPosting] = Field(default_factory=list)
    totalFound: int = 0


def _smartrecruiters(client: httpx.Client, company: Company) -> list[RawOffer]:
    url = f"https://api.smartrecruiters.com/v1/companies/{company.board}/postings"
    postings: list[_SrPosting] = []
    offset = 0
    while True:
        page = _SrResponse.model_validate(
            _get(client, url, limit=SMARTRECRUITERS_PAGE, offset=offset)
        )
        postings += page.content
        offset += SMARTRECRUITERS_PAGE
        if not page.content or offset >= page.totalFound:
            break
    return [
        RawOffer(
            source=NAME,
            external_id=f"smartrecruiters:{company.board}:{p.id}",
            company=company.name,
            title=p.name,
            location=p.location.fullLocation or p.location.city,
            contract=classify_contract(p.name, p.typeOfEmployment.id, p.typeOfEmployment.label),
            remote=p.location.remote,
            url=f"https://jobs.smartrecruiters.com/{company.board}/{p.id}",
            published_at=parse_datetime(p.releasedDate),
        )
        for p in postings
    ]


# Recruitee ----------------------------------------------------------------------------------


class _RecruiteeOffer(Payload):
    id: int
    title: str
    location: str | None = None
    careers_url: str | None = None
    description: str | None = None
    published_at: str | None = None
    employment_type_code: str | None = None
    remote: bool | None = None


class _RecruiteeResponse(Payload):
    offers: list[_RecruiteeOffer] = Field(default_factory=list)


def _recruitee(client: httpx.Client, company: Company) -> list[RawOffer]:
    url = f"https://{company.board}.recruitee.com/api/offers/"
    payload = _RecruiteeResponse.model_validate(_get(client, url))
    return [
        RawOffer(
            source=NAME,
            external_id=f"recruitee:{company.board}:{o.id}",
            company=company.name,
            title=o.title,
            location=o.location,
            # Codes look like "fulltime_permanent" or "internship".
            contract=classify_contract(o.title, (o.employment_type_code or "").replace("_", " ")),
            remote=o.remote,
            url=o.careers_url,
            description=html_to_text(o.description),
            published_at=parse_datetime(o.published_at),
        )
        for o in payload.offers
    ]


_FETCHERS: dict[Ats, Callable[[httpx.Client, Company], list[RawOffer]]] = {
    Ats.GREENHOUSE: _greenhouse,
    Ats.LEVER: _lever,
    Ats.ASHBY: _ashby,
    Ats.SMARTRECRUITERS: _smartrecruiters,
    Ats.RECRUITEE: _recruitee,
}


def covers_area(watch: WatchConfig) -> bool:
    # Boards list every office of the company.
    return False


def _mentions(text: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(p.search(text) for p in patterns)


def search(client: httpx.Client, watch: WatchConfig, secrets: dict[str, str]) -> list[RawOffer]:
    """Every listed company; one failing board is reported without hiding the others."""
    if not watch.companies:
        raise MissingCriteria("aucune entreprise suivie dans watch.companies")
    offers: list[RawOffer] = []
    failures: list[str] = []
    for company in watch.companies:
        try:
            offers += _FETCHERS[company.ats](client, company)
        except SourceError as error:
            failures.append(f"{company.name} : {error}")
        except ValueError:
            failures.append(f"{company.name} : réponse inattendue")
    # Boards are not searched by keyword: the user's keywords pick the relevant postings.
    if watch.keywords:
        patterns = [phrase_pattern(k) for k in watch.keywords]
        offers = [o for o in offers if _mentions(norm(f"{o.title} {o.description}"), patterns)]
    if failures:
        raise PartialResult(" ; ".join(failures), offers)
    return offers
