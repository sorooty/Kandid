"""France Travail, Offres d'emploi v2 (free application on francetravail.io, OAuth2).

The token URL, scope, parameter and field names come from consistent third-party documentation (the
official page needs a logged-in account): they are checked on the first real call, see
docs/specs/v2-veille.md. Every response field but the id and title is optional, so a renamed one
degrades instead of failing.
"""

import httpx
from pydantic import Field

from kandid_tools.config import ContractKind, WatchConfig
from kandid_tools.sources.base import (
    UNKNOWN_COMPANY,
    Payload,
    RawOffer,
    SourceError,
    classify_contract,
    json_body,
    parse_datetime,
    request,
)

NAME = "francetravail"
TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
SCOPE = "api_offresdemploiv2 o2dsoffre"
# The API caps a search at 150 results per call.
PAGE = "0-149"
# Accepted values of `publieeDepuis`, in days.
_FRESHNESS = (1, 3, 7, 14, 31)
_CONTRACT_CODES = {
    "CDI": ContractKind.PERMANENT,
    "CDD": ContractKind.FIXED_TERM,
    "MIS": ContractKind.TEMPORARY,
    "LIB": ContractKind.FREELANCE,
}


class _Token(Payload):
    access_token: str


class _Place(Payload):
    libelle: str | None = None


class _Company(Payload):
    nom: str | None = None


class _Origin(Payload):
    urlOrigine: str | None = None


class _Offer(Payload):
    id: str
    intitule: str
    description: str = ""
    dateCreation: str | None = None
    lieuTravail: _Place = _Place()
    entreprise: _Company = _Company()
    typeContrat: str | None = None
    typeContratLibelle: str | None = None
    natureContrat: str | None = None
    alternance: bool = False
    origineOffre: _Origin = _Origin()


class _Response(Payload):
    resultats: list[_Offer] = Field(default_factory=list)


def _token(client: httpx.Client, secrets: dict[str, str]) -> str:
    response = request(
        client,
        "POST",
        TOKEN_URL,
        params={"realm": "/partenaire"},
        data={
            "grant_type": "client_credentials",
            "client_id": secrets["client_id"],
            "client_secret": secrets["client_secret"],
            "scope": SCOPE,
        },
    )
    try:
        return _Token.model_validate(json_body(response)).access_token
    except ValueError:
        raise SourceError("jeton France Travail illisible") from None


def covers_area(watch: WatchConfig) -> bool:
    return bool(watch.area.departements)


def _params(watch: WatchConfig) -> dict[str, str]:
    params = {"range": PAGE}
    if watch.keywords:
        params["motsCles"] = ",".join(watch.keywords)
    if watch.area.departements:
        params["departement"] = ",".join(watch.area.departements)
    freshness = next((d for d in _FRESHNESS if d >= watch.max_age_days), _FRESHNESS[-1])
    params["publieeDepuis"] = str(freshness)
    # Contracts are filtered after the call, on the `alternance` flag and `typeContrat`: no
    # contract code is sent that the official page could not confirm.
    return params


def _contract(offer: _Offer) -> ContractKind | None:
    if offer.alternance:
        return ContractKind.WORK_STUDY
    return _CONTRACT_CODES.get(offer.typeContrat or "") or classify_contract(
        offer.typeContratLibelle, offer.intitule
    )


def search(client: httpx.Client, watch: WatchConfig, secrets: dict[str, str]) -> list[RawOffer]:
    token = _token(client, secrets)
    response = request(
        client,
        "GET",
        SEARCH_URL,
        params=_params(watch),
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    # 204 means no offer matches.
    if response.status_code == 204 or not response.content:
        return []
    try:
        payload = _Response.model_validate(json_body(response))
    except ValueError:
        raise SourceError("réponse inattendue de France Travail") from None
    return [
        RawOffer(
            source=NAME,
            external_id=offer.id,
            company=offer.entreprise.nom or UNKNOWN_COMPANY,
            title=offer.intitule,
            location=offer.lieuTravail.libelle,
            contract=_contract(offer),
            url=offer.origineOffre.urlOrigine
            or f"https://candidat.francetravail.fr/offres/recherche/detail/{offer.id}",
            description=offer.description,
            published_at=parse_datetime(offer.dateCreation),
        )
        for offer in payload.resultats
    ]
