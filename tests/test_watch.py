import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
import yaml
from sqlmodel import select
from typer.testing import CliRunner

from kandid_tools import watch as watch_module
from kandid_tools.cli import app
from kandid_tools.config import Area, Config, ContractKind, WatchConfig
from kandid_tools.db import Application, Event, Offer, Run, open_db, session
from kandid_tools.dedup import fingerprint
from kandid_tools.scoring import profile_skills, score
from kandid_tools.sources import linkedin_guest
from kandid_tools.sources.base import RawOffer, client
from kandid_tools.status import Status
from kandid_tools.watch import area_match, run_watch

from conftest import CAMILLE

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sources"
TODAY = datetime(2026, 10, 30, 12, tzinfo=UTC)
LBA_TOKEN = "SECRET-LBA-123"
FT_SECRET = "SECRET-FT-456"
ROUTES = {
    "boards-api.greenhouse.io/v1/boards/ghco/jobs": "greenhouse.json",
    "recco.recruitee.com/api/offers/": "recruitee.json",
    "api.apprentissage.beta.gouv.fr/api/job/v1/search": "labonnealternance.json",
    "entreprise.francetravail.fr/connexion/oauth2/access_token": "francetravail_token.json",
    "api.francetravail.io/partenaire/offresdemploi/v2/offres/search": "francetravail_search.json",
}
CONFIG = {
    "watch": {
        "contracts": ["alternance", "stage"],
        "keywords": ["data"],
        "romes": ["M1403"],
        "area": {"city": "Lyon", "departements": ["69"]},
        "exclude": ["comptable"],
        "companies": [
            {"name": "Gh Co", "ats": "greenhouse", "board": "ghco"},
            {"name": "Rec Co", "ats": "recruitee", "board": "recco"},
        ],
        "sources": {"linkedin_guest": {"enabled": True}},
    }
}


def handler(request: httpx.Request) -> httpx.Response:
    path = f"{request.url.host}{request.url.path}"
    if request.url.host == "www.linkedin.com":
        first_page = request.url.params["start"] == "0"
        body = (FIXTURES / "linkedin.html").read_bytes() if first_page else b""
        return httpx.Response(200, content=body)
    return httpx.Response(200, content=(FIXTURES / ROUTES[path]).read_bytes())


@pytest.fixture
def setup(monkeypatch, tmp_path):
    monkeypatch.setenv("KANDID_LBA_TOKEN", LBA_TOKEN)
    monkeypatch.setenv("KANDID_FT_CLIENT_ID", "ft-id")
    monkeypatch.setenv("KANDID_FT_CLIENT_SECRET", FT_SECRET)
    monkeypatch.delenv("KANDID_ADZUNA_APP_ID", raising=False)
    monkeypatch.setattr(linkedin_guest, "PAUSE", 0)
    monkeypatch.setattr(watch_module, "now", lambda: TODAY)
    monkeypatch.setattr(
        watch_module, "client", lambda transport=None: client(httpx.MockTransport(handler))
    )
    config = Config.model_validate(CONFIG | {"paths": {"data": str(tmp_path)}})
    return config, open_db(tmp_path)


def test_fingerprint_ignores_legal_forms_gender_and_accents():
    assert fingerprint("Lumio Énergie SAS", "Data Analyst H/F") == fingerprint(
        "LUMIO ENERGIE", "Data analyst (F/H)"
    )
    assert fingerprint("Acme", "Data Analyst") != fingerprint("Acme", "Data Engineer")


def test_score_explains_itself(profile):
    offer = RawOffer(
        source="x",
        external_id="1",
        company="Acme",
        title="Alternance Data Analyst",
        location="Lyon",
        contract=ContractKind.WORK_STUDY,
        description="Python, SQL, pandas, Power BI et Excel au quotidien.",
        published_at=TODAY - timedelta(days=2),
    )
    watch = WatchConfig(contracts=["alternance"], keywords=["data analyst"])
    result = score(offer, watch, profile_skills(profile), in_area=True, today=TODAY)
    assert result.score == 100
    assert "titre : data analyst" in result.justification
    assert "compétences : Python, SQL" in result.justification
    assert result.points_to_check == []


def test_score_flags_unknowns(profile):
    offer = RawOffer(source="x", external_id="1", company="Acme", title="Poste", intermediary=True)
    result = score(offer, WatchConfig(keywords=["data"]), [], in_area=None, today=TODAY)
    assert result.score == round(25 / 2 + 15 / 2 + 10 / 2)
    assert result.points_to_check == [
        "type de contrat non précisé",
        "lieu non précisé",
        "publiée par une école ou un intermédiaire",
        "description absente : lire l'offre sur le site",
    ]


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("Lyon, France", True),
        ("69 - Villeurbanne", True),
        ("69100 Villeurbanne", True),
        ("Paris", False),
        ("690 avenue X, 13001 Marseille", False),
        ("Paris 15e", False),
        ("Villeurbanne (69)", True),
        (None, None),
    ],
)
def test_area_match(location, expected):
    offer = RawOffer(source="x", external_id="1", company="A", title="T", location=location)
    assert area_match(offer, Area(city="Lyon", departements=["69"]), covered=False) is expected


def test_overseas_department_postal_code():
    offer = RawOffer(
        source="x", external_id="1", company="A", title="T", location="97100 Basse-Terre"
    )
    assert area_match(offer, Area(departements=["971"]), covered=False) is True


def test_skill_with_separators_or_details_matches_its_parts():
    offer = RawOffer(
        source="x", external_id="1", company="A", title="T", description="CSS et Excel"
    )
    result = score(offer, WatchConfig(), ["HTML/CSS", "Excel (avancé)"], in_area=True, today=TODAY)
    assert "compétences : HTML/CSS, Excel (avancé)" in result.justification


def _offer(**fields) -> RawOffer:
    return RawOffer(source="careers", company="Acme", title="Data analyst", **fields)


def test_same_title_in_two_places_of_one_source_is_two_offers(setup):
    _config, engine = setup
    store = watch_module._Store(watch_module.session(engine))
    offers = [
        _offer(external_id="1", location="Lyon"),
        _offer(external_id="2", location="Lyon 3e"),
        _offer(external_id="3", location="Lyon"),
    ]
    report, _ = watch_module._process(
        store,
        offers,
        covered=True,
        watch=WatchConfig(),
        skills=[],
        run_id=None,
        dry_run=True,
        today=TODAY,
    )
    assert (report.kept, report.duplicates) == (2, 1)


def test_anonymous_offers_are_never_merged(setup):
    _config, engine = setup
    store = watch_module._Store(watch_module.session(engine))
    offers = [
        RawOffer(source="francetravail", external_id=str(i), company="?", title="Vendeur")
        for i in range(3)
    ]
    report, _ = watch_module._process(
        store,
        offers,
        covered=True,
        watch=WatchConfig(),
        skills=[],
        run_id=None,
        dry_run=True,
        today=TODAY,
    )
    assert report.kept == 3


def test_remote_offer_matches_when_accepted():
    offer = RawOffer(
        source="x", external_id="1", company="A", title="T", location="Paris", remote=True
    )
    assert area_match(offer, Area(city="Lyon", remote=True), covered=False) is True
    assert area_match(offer, Area(city="Lyon"), covered=False) is False


def test_watch_stores_filters_and_dedups(setup):
    config, engine = setup
    report = run_watch(config, engine, ["Python", "SQL"])
    sources = report.sources
    # The marketing posting does not mention "data": dropped before scoring.
    assert (sources["careers"].fetched, sources["careers"].kept) == (1, 1)
    assert sources["labonnealternance"].kept == 2
    assert sources["francetravail"].kept == 1 and sources["francetravail"].filtered == 1
    assert (
        sources["adzuna"].skipped
        == "identifiants absents (KANDID_ADZUNA_APP_ID, KANDID_ADZUNA_APP_KEY)"
    )
    assert sources["linkedin_guest"].duplicates == 1 and sources["linkedin_guest"].kept == 1
    assert len(report.new) == 5
    with session(engine) as db:
        offers = db.exec(select(Offer)).all()
        assert len(offers) == 5
        assert {a.status for a in db.exec(select(Application)).all()} == {Status.TO_REVIEW}
        assert len(db.exec(select(Event)).all()) == 5
        lba = db.exec(select(Offer).where(Offer.external_id == "France Travail:100")).one()
        assert lba.also_on == [
            {
                "source": "linkedin_guest",
                "url": "https://fr.linkedin.com/jobs/view/data-analyst-3900000001",
            }
        ]
        assert "publiée par une école ou un intermédiaire" in lba.points_to_check

    second = run_watch(config, engine, ["Python", "SQL"])
    assert second.new == []
    with session(engine) as db:
        assert len(db.exec(select(Offer)).all()) == 5
        lba = db.exec(select(Offer).where(Offer.external_id == "France Travail:100")).one()
        assert len(lba.also_on) == 1
        runs = db.exec(select(Run)).all()
        assert [r.counts["labonnealternance"]["duplicates"] for r in runs] == [0, 2]


def test_dry_run_stores_no_offer(setup):
    config, engine = setup
    report = run_watch(config, engine, [], dry_run=True)
    assert len(report.new) == 5
    with session(engine) as db:
        assert db.exec(select(Offer)).all() == []
        assert db.exec(select(Run)).one().dry_run


def test_one_failing_source_does_not_stop_the_others(setup, monkeypatch):
    config, engine = setup

    def broken(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.apprentissage.beta.gouv.fr":
            return httpx.Response(401)
        return handler(request)

    monkeypatch.setattr(
        watch_module, "client", lambda transport=None: client(httpx.MockTransport(broken))
    )
    report = run_watch(config, engine, [])
    assert report.sources["labonnealternance"].error.startswith("accès refusé")
    assert report.sources["francetravail"].kept == 1


def test_unknown_source_is_refused(setup):
    config, engine = setup
    with pytest.raises(ValueError, match="source inconnue"):
        run_watch(config, engine, [], only="indeed")


def test_no_secret_in_database_or_output(setup, tmp_path):
    config, engine = setup
    report = run_watch(config, engine, [])
    engine.dispose()
    stored = (tmp_path / "kandid.db").read_bytes()
    output = report.model_dump_json()
    for secret in (LBA_TOKEN, FT_SECRET, "fake-access-token"):
        assert secret.encode() not in stored
        assert secret not in output


def test_cli_watch_list_add_and_discard(setup, tmp_path):
    runner = CliRunner()
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.safe_dump(CONFIG | {"paths": {"data": str(tmp_path)}}), encoding="utf-8"
    )
    common = ["--config", str(config_file)]
    profile = ["--profile", str(CAMILLE / "profile.yaml")]

    result = runner.invoke(app, ["veille", *common, *profile])
    assert result.exit_code == 0, result.output
    assert "5 nouvelle(s) offre(s)" in result.stdout
    assert LBA_TOKEN not in result.output

    added = runner.invoke(
        app,
        [
            "offre",
            "ajouter",
            "--entreprise",
            "Optimo",
            "--titre",
            "Alternance data",
            "--contrat",
            "alternance",
            *common,
            "--json",
        ],
    )
    assert added.exit_code == 0, added.output
    offer_id = json.loads(added.stdout)["id"]
    again = runner.invoke(
        app,
        ["offre", "ajouter", "--entreprise", "OPTIMO", "--titre", "Alternance Data H/F", *common],
    )
    assert again.exit_code == 1
    assert "déjà enregistrée" in again.stderr

    discarded = runner.invoke(
        app, ["offre", "ecarter", str(offer_id), "--raison", "trop loin", *common]
    )
    assert discarded.exit_code == 0, discarded.output
    assert (
        runner.invoke(app, ["offre", "ecarter", str(offer_id), "--raison", "x", *common]).exit_code
        == 1
    )

    listed = runner.invoke(app, ["offres", "--status", "archived", *common, "--json"])
    assert [row["id"] for row in json.loads(listed.stdout)] == [offer_id]
    everything = json.loads(runner.invoke(app, ["offres", *common, "--json"]).stdout)
    # Archived offers are hidden unless asked for.
    assert len(everything) == 5
    assert everything == sorted(everything, key=lambda row: -row["score"])
