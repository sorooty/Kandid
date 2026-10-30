import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from kandid_tools.config import Ats, Company, ContractKind, WatchConfig
from kandid_tools.sources import (
    adzuna,
    careers,
    francetravail,
    labonnealternance,
    linkedin_guest,
)
from kandid_tools.sources.base import (
    MissingCriteria,
    PartialResult,
    RawOffer,
    SourceError,
    classify_contract,
    client,
    html_to_text,
    parse_datetime,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sources"
SECRETS = {
    "token": "t",
    "client_id": "id",
    "client_secret": "secret",
    "app_id": "a",
    "app_key": "k",
}


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def http(
    routes: dict[str, httpx.Response], seen: list[httpx.Request] | None = None
) -> httpx.Client:
    """A client answering by host and path, recording each request."""

    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return routes.get(f"{request.url.host}{request.url.path}", httpx.Response(404))

    return client(httpx.MockTransport(handler))


def ok(name: str) -> httpx.Response:
    return httpx.Response(200, content=fixture(name))


def test_labonnealternance_reads_jobs_only():
    seen: list[httpx.Request] = []
    routes = {"api.apprentissage.beta.gouv.fr/api/job/v1/search": ok("labonnealternance.json")}
    watch = WatchConfig(romes=["M1403"], area={"departements": ["69"]})
    offers = labonnealternance.search(http(routes, seen), watch, SECRETS)
    assert [o.external_id for o in offers] == ["France Travail:100", "Hellowork:200"]
    first = offers[0]
    assert (first.company, first.contract, first.intermediary) == (
        "Lumio Énergie",
        ContractKind.WORK_STUDY,
        True,
    )
    assert first.description == "Python et SQL au quotidien."
    assert seen[0].headers["Authorization"] == "Bearer t"
    assert seen[0].url.params.get_list("departements") == ["69"]


def test_labonnealternance_needs_romes():
    with pytest.raises(MissingCriteria, match="ROME"):
        labonnealternance.search(http({}), WatchConfig(), SECRETS)


def test_francetravail_token_then_search():
    seen: list[httpx.Request] = []
    routes = {
        "entreprise.francetravail.fr/connexion/oauth2/access_token": ok("francetravail_token.json"),
        "api.francetravail.io/partenaire/offresdemploi/v2/offres/search": ok(
            "francetravail_search.json"
        ),
    }
    watch = WatchConfig(keywords=["data"], max_age_days=10)
    offers = francetravail.search(http(routes, seen), watch, SECRETS)
    assert [o.contract for o in offers] == [ContractKind.WORK_STUDY, ContractKind.PERMANENT]
    assert offers[0].url == "https://candidat.francetravail.fr/offres/recherche/detail/201ABCD"
    assert offers[1].company == "?"
    assert seen[1].headers["Authorization"] == "Bearer fake-access-token"
    assert seen[1].url.params["publieeDepuis"] == "14"


def test_francetravail_no_content():
    routes = {
        "entreprise.francetravail.fr/connexion/oauth2/access_token": ok("francetravail_token.json"),
        "api.francetravail.io/partenaire/offresdemploi/v2/offres/search": httpx.Response(204),
    }
    assert francetravail.search(http(routes), WatchConfig(), SECRETS) == []


def test_adzuna_cleans_markup_and_dedups_keywords():
    routes = {"api.adzuna.com/v1/api/jobs/fr/search/1": ok("adzuna.json")}
    watch = WatchConfig(keywords=["data", "analyst"], area={"city": "Lyon"})
    offers = adzuna.search(http(routes), watch, SECRETS)
    assert len(offers) == 1
    assert offers[0].title == "Data Analyst en alternance"
    assert offers[0].contract == ContractKind.WORK_STUDY
    assert offers[0].description.startswith("Mission & reporting SQL")


def test_careers_every_ats(monkeypatch):
    # Two pages of one posting each.
    monkeypatch.setattr(careers, "SMARTRECRUITERS_PAGE", 1)
    companies = [
        Company(name="Gh Co", ats=Ats.GREENHOUSE, board="ghco"),
        Company(name="Lever Co", ats=Ats.LEVER, board="leverco"),
        Company(name="Ashby Co", ats=Ats.ASHBY, board="ashbyco"),
        Company(name="Sr Co", ats=Ats.SMARTRECRUITERS, board="SrCo"),
        Company(name="Rec Co", ats=Ats.RECRUITEE, board="recco"),
    ]
    pages = iter([ok("smartrecruiters_1.json"), ok("smartrecruiters_2.json")])

    def handler(request: httpx.Request) -> httpx.Response:
        path = f"{request.url.host}{request.url.path}"
        routes = {
            "boards-api.greenhouse.io/v1/boards/ghco/jobs": "greenhouse.json",
            "api.lever.co/v0/postings/leverco": "lever.json",
            "api.ashbyhq.com/posting-api/job-board/ashbyco": "ashby.json",
            "recco.recruitee.com/api/offers/": "recruitee.json",
        }
        if path == "api.smartrecruiters.com/v1/companies/SrCo/postings":
            return next(pages)
        return ok(routes[path])

    offers = careers.search(
        client(httpx.MockTransport(handler)), WatchConfig(companies=companies), {}
    )
    by_id = {o.external_id: o for o in offers}
    assert set(by_id) == {
        "greenhouse:ghco:501",
        "lever:leverco:lv-1",
        "ashby:ashbyco:as-1",
        "smartrecruiters:SrCo:sr-1",
        "smartrecruiters:SrCo:sr-2",
        "recruitee:recco:77",
    }
    assert by_id["greenhouse:ghco:501"].description == "Python & SQL"
    assert by_id["greenhouse:ghco:501"].contract == ContractKind.INTERNSHIP
    assert by_id["lever:leverco:lv-1"].contract == ContractKind.WORK_STUDY
    assert by_id["ashby:ashbyco:as-1"].remote is True
    assert by_id["ashby:ashbyco:as-1"].contract == ContractKind.INTERNSHIP
    assert by_id["recruitee:recco:77"].contract == ContractKind.FIXED_TERM
    assert by_id["recruitee:recco:77"].published_at == datetime(2026, 10, 6, 14, 54, 28, tzinfo=UTC)


def test_careers_one_failing_board_does_not_hide_the_others():
    companies = [
        Company(name="Gone", ats=Ats.GREENHOUSE, board="gone"),
        Company(name="Rec Co", ats=Ats.RECRUITEE, board="recco"),
    ]
    routes = {"recco.recruitee.com/api/offers/": ok("recruitee.json")}
    with pytest.raises(PartialResult, match="Gone : erreur HTTP 404") as partial:
        careers.search(http(routes), WatchConfig(companies=companies), {})
    assert [o.company for o in partial.value.offers] == ["Rec Co"]


def test_careers_keeps_postings_mentioning_a_keyword():
    companies = [Company(name="Rec Co", ats=Ats.RECRUITEE, board="recco")]
    routes = {"recco.recruitee.com/api/offers/": ok("recruitee.json")}
    found = careers.search(
        http(routes), WatchConfig(companies=companies, keywords=["réseaux sociaux"]), {}
    )
    assert len(found) == 1
    assert (
        careers.search(http(routes), WatchConfig(companies=companies, keywords=["data"]), {}) == []
    )


@pytest.mark.parametrize(
    ("module", "watch"),
    [
        (labonnealternance, WatchConfig()),
        (adzuna, WatchConfig()),
        (linkedin_guest, WatchConfig()),
        (careers, WatchConfig()),
    ],
)
def test_missing_criteria_is_not_a_failure(module, watch):
    with pytest.raises(MissingCriteria):
        module.search(http({}), watch, SECRETS)


def test_linkedin_parses_cards_and_stops_on_empty_page(monkeypatch):
    monkeypatch.setattr(linkedin_guest, "PAUSE", 0)
    pages = iter([fixture("linkedin.html"), b""])
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=next(pages))

    watch = WatchConfig(keywords=["data"], area={"city": "Lyon"}, max_age_days=2)
    offers = linkedin_guest.search(client(httpx.MockTransport(handler)), watch, {})
    assert [o.title for o in offers] == [
        "Alternance Data Analyst (F/H)",
        "Stage contrôle de gestion",
    ]
    first = offers[0]
    assert first.company == "Lumio Énergie"
    assert first.url == "https://fr.linkedin.com/jobs/view/data-analyst-3900000001"
    assert first.location == "Lyon, Auvergne-Rhône-Alpes, France"
    assert offers[1].url == "https://www.linkedin.com/jobs/view/3900000002"
    assert [r.url.params["start"] for r in seen] == ["0", "2"]
    assert seen[0].url.params["f_TPR"] == "r172800"


def test_linkedin_rate_limit_keeps_what_was_read(monkeypatch):
    monkeypatch.setattr(linkedin_guest, "PAUSE", 0)
    pages = iter([httpx.Response(200, content=fixture("linkedin.html")), httpx.Response(429)])
    transport = httpx.MockTransport(lambda request: next(pages))
    with pytest.raises(PartialResult, match="limite de requêtes") as partial:
        linkedin_guest.search(client(transport), WatchConfig(keywords=["data"]), {})
    assert len(partial.value.offers) == 2


@pytest.mark.parametrize(
    ("status", "message"),
    [(401, "accès refusé"), (429, "limite de requêtes"), (404, "erreur HTTP 404")],
)
def test_http_errors_become_source_errors(status, message):
    routes = {"api.apprentissage.beta.gouv.fr/api/job/v1/search": httpx.Response(status, text="x")}
    with pytest.raises(SourceError, match=message):
        labonnealternance.search(http(routes), WatchConfig(romes=["M1403"]), SECRETS)


def test_server_error_is_retried_once():
    answers = iter([httpx.Response(503), ok("adzuna.json")])
    transport = httpx.MockTransport(lambda request: next(answers))
    offers = adzuna.search(client(transport), WatchConfig(keywords=["data"]), SECRETS)
    assert len(offers) == 1


def test_malformed_json_is_reported_without_body():
    secret_body = "<html>token=t</html>"
    routes = {"api.adzuna.com/v1/api/jobs/fr/search/1": httpx.Response(200, text=secret_body)}
    with pytest.raises(SourceError) as error:
        adzuna.search(http(routes), WatchConfig(keywords=["data"]), SECRETS)
    assert "token" not in str(error.value)


def test_unexpected_shape_is_reported():
    routes = {
        "api.adzuna.com/v1/api/jobs/fr/search/1": httpx.Response(
            200, content=json.dumps({"results": [{"id": "1"}]}).encode()
        )
    }
    with pytest.raises(SourceError, match="réponse inattendue"):
        adzuna.search(http(routes), WatchConfig(keywords=["data"]), SECRETS)


@pytest.mark.parametrize(
    ("texts", "expected"),
    [
        (("Contrat d'apprentissage en CDD",), ContractKind.WORK_STUDY),
        (("Stage de fin d'études",), ContractKind.INTERNSHIP),
        (("Software Engineer Intern",), ContractKind.INTERNSHIP),
        (("Internal auditor",), None),
        (("CDI temps plein",), ContractKind.PERMANENT),
        ((None, "Mission freelance"), ContractKind.FREELANCE),
    ],
)
def test_classify_contract(texts, expected):
    assert classify_contract(*texts) == expected


def test_text_helpers():
    assert html_to_text("<p>Un</p><p>Deux &amp; trois</p>") == "Un\nDeux & trois"
    assert parse_datetime(0) == datetime(1970, 1, 1, tzinfo=UTC)
    assert parse_datetime("2026-10-06") == datetime(2026, 10, 6, tzinfo=UTC)
    assert parse_datetime("demain") is None


def test_raw_offer_drops_unsafe_values():
    offer = RawOffer(
        source="x",
        external_id="1",
        company="Acme\x1b[2J",
        title="Poste\x9b31m",
        url="javascript:alert(1)",
        description="Ligne 1\nLigne 2",
    )
    assert (offer.company, offer.title, offer.url) == ("Acme[2J", "Poste31m", None)
    assert offer.description == "Ligne 1\nLigne 2"


def test_any_httpx_error_becomes_a_source_error_without_url():
    def redirect_loop(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"Location": str(request.url)})

    with pytest.raises(SourceError) as error:
        adzuna.search(
            client(httpx.MockTransport(redirect_loop)), WatchConfig(keywords=["d"]), SECRETS
        )
    assert str(error.value) == "requête échouée (TooManyRedirects)"
    assert error.value.__cause__ is None


def test_secret_pasted_instead_of_variable_name_is_refused():
    with pytest.raises(ValueError) as error:
        WatchConfig(sources={"adzuna": {"env": {"app_key": "abc123-secret"}}})
    assert "abc123-secret" not in str(error.value.errors(include_input=False))
