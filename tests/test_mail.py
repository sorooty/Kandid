import json
from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from kandid_tools import tracking
from kandid_tools.cli import app
from kandid_tools.config import MailConfig, WatchConfig
from kandid_tools.db import open_db
from kandid_tools.mail import Kind, Mail, classify, is_noise, suggest
from kandid_tools.sources.base import RawOffer
from kandid_tools.status import Status
from kandid_tools.watch import add_offer

CONFIG = MailConfig()
DAY = datetime(2026, 11, 3, 10, tzinfo=UTC)


def mail(subject: str, sender: str = "rh@exemple.fr", preview: str = "", **extra) -> Mail:
    return Mail(source="gmail", id=subject[:10], sender=sender, subject=subject, preview=preview,
                date=extra.get("date", DAY))  # fmt: skip


@pytest.fixture
def engine(tmp_path):
    engine = open_db(tmp_path)
    for company in ["Nordlys", "Datavia", "Datavia Labs", "Maison Tisserand"]:
        offer = RawOffer(
            source="careers", external_id=company, company=company, title="Data analyst"
        )
        add_offer(engine, offer, WatchConfig(), [])
    return engine


def sent(engine, offer_id: int) -> None:
    for status in (Status.TO_PREPARE, Status.READY, Status.SENT):
        tracking.change_status(engine, offer_id, status, at=datetime(2026, 10, 20, tzinfo=UTC))


def test_alerts_and_newsletters_are_noise():
    assert is_noise(mail("Data analyst à Nordlys", sender="donotreply@jobalert.indeed.com"), CONFIG)
    assert is_noise(mail("12 offres d'emploi supplémentaires pour vous"), CONFIG)
    assert not is_noise(mail("Votre candidature chez Nordlys"), CONFIG)


@pytest.mark.parametrize(
    ("subject", "preview", "kind"),
    [
        ("Votre candidature", "Nous ne pouvons pas donner une suite favorable", Kind.REJECTION),
        ("Votre candidature", "Le poste a été pourvu, merci de votre intérêt", Kind.REJECTION),
        ("Suite à notre entretien", "nous avons retenu d'autres profils", Kind.REJECTION),
        ("Proposition d'entretien", "Quelles sont vos disponibilités ?", Kind.INTERVIEW),
        ("Bien reçu ! Votre candidature", "", Kind.ACKNOWLEDGEMENT),
        ("Thank you for applying", "", Kind.ACKNOWLEDGEMENT),
        ("Bienvenue sur notre espace carrière", "", Kind.OTHER),
    ],
)
def test_classify(subject, preview, kind):
    assert classify(mail(subject, preview=preview), CONFIG) is kind


def test_suggest_matches_company_and_checks_transitions(engine):
    sent(engine, 1)
    sent(engine, 3)
    tracking.change_status(engine, 4, Status.TO_PREPARE)
    tracking.change_status(engine, 4, Status.READY)
    mails = [
        mail("Votre candidature", sender="talent@nordlys.teamtailor-mail.com",
             preview="nous ne pouvons pas donner une suite favorable"),
        mail("Entretien Datavia Labs", preview="vos disponibilités pour un échange"),
        mail("Candidature reçue chez Maison Tisserand"),
        mail("Bien reçu ! Votre candidature chez Datavia", date=datetime(2026, 10, 1, tzinfo=UTC)),
        mail("Votre candidature chez Inconnue SA", preview="suite favorable"),
        mail("Offre à Nordlys", sender="jobalerts-noreply@linkedin.com"),
    ]  # fmt: skip
    analysis = suggest(engine, mails, CONFIG)
    assert analysis.ignored == 1
    by_subject = {s.mail.subject: s for s in analysis.suggestions}
    refusal = by_subject["Votre candidature"]
    assert (refusal.offer_id, refusal.kind, refusal.target) == (1, Kind.REJECTION, Status.REJECTED)
    # "Datavia Labs" is the longer name: it wins over "Datavia".
    interview = by_subject["Entretien Datavia Labs"]
    assert (interview.offer_id, interview.target) == (3, Status.INTERVIEW)
    acknowledged = by_subject["Candidature reçue chez Maison Tisserand"]
    assert (acknowledged.current, acknowledged.target) == (Status.READY, Status.SENT)
    # Datavia was never sent: an acknowledgement cannot jump "À voir" to "Envoyée".
    assert by_subject["Bien reçu ! Votre candidature chez Datavia"].target is None
    assert by_subject["Votre candidature chez Inconnue SA"].offer_id is None


def test_mail_older_than_last_change_is_not_proposed_again(engine):
    sent(engine, 1)
    refusal = mail("Votre candidature Nordlys", preview="suite favorable")
    tracking.change_status(engine, 1, Status.REJECTED, at=DAY)
    assert suggest(engine, [refusal], CONFIG).suggestions[0].target is None


def test_second_application_at_the_same_company_gets_the_answer(engine):
    sent(engine, 2)
    tracking.change_status(engine, 2, Status.REJECTED, at=datetime(2026, 10, 25, tzinfo=UTC))
    again = RawOffer(source="careers", external_id="datavia-2", company="Datavia",
                     title="Alternance data engineer")  # fmt: skip
    add_offer(engine, again, WatchConfig(), [])
    sent(engine, 5)
    refusal = mail("Votre candidature Datavia", preview="nous avons retenu d'autres profils")
    found = suggest(engine, [refusal], CONFIG).suggestions[0]
    assert (found.offer_id, found.target) == (5, Status.REJECTED)


def test_common_word_in_the_preview_does_not_beat_the_subject(engine):
    sent(engine, 1)
    sent(engine, 4)
    answer = mail(
        "Votre candidature chez Maison Tisserand", preview="Nordlys et nous, suite favorable"
    )
    assert suggest(engine, [answer], CONFIG).suggestions[0].offer_id == 4


def test_cli_analyse_and_dated_status(engine, tmp_path):
    sent(engine, 1)
    config = tmp_path / "config.yaml"
    config.write_text(f"paths:\n  data: {tmp_path.as_posix()}\n", encoding="utf-8")
    mails = tmp_path / "mails.json"
    found = mail("Votre candidature Nordlys", preview="suite favorable")
    mails.write_text(json.dumps([found.model_dump(mode="json")]), encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        app, ["courrier", "analyser", str(mails), "--config", str(config), "--json"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["suggestions"][0]["target"] == "rejected"
    future = ["offre", "statut", "1", "rejected", "--date", "2999-01-01", "--config", str(config)]
    assert "futur" in runner.invoke(app, future).output
    args = ["offre", "statut", "1", "rejected", "--date", "2026-10-31", "--config", str(config)]
    assert runner.invoke(app, args).exit_code == 0
    events = tracking.offer_view(engine, 1).events
    refusal = next(e for e in events if e.kind == "status" and e.detail == "rejected")
    assert refusal.at.date().isoformat() == "2026-10-31"
    bad = runner.invoke(
        app, ["offre", "statut", "1", "interview", "--date", "3/11", "--config", str(config)]
    )
    assert bad.exit_code == 1
    assert "date invalide" in bad.output
