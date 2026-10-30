import json
from datetime import UTC, datetime, timedelta

import pytest
import yaml
from sqlmodel import select
from typer.testing import CliRunner

from kandid_tools import tracking
from kandid_tools.cli import app
from kandid_tools.config import WatchConfig
from kandid_tools.db import Application, open_db, session
from kandid_tools.sources.base import RawOffer
from kandid_tools.status import Status
from kandid_tools.watch import add_offer

TODAY = datetime(2026, 11, 20, 9, tzinfo=UTC)


@pytest.fixture
def engine(tmp_path):
    engine = open_db(tmp_path)
    for n, source in enumerate(["careers", "francetravail", "francetravail"], start=1):
        offer = RawOffer(source=source, external_id=str(n), company=f"Société {n}", title="Poste")
        add_offer(engine, offer, WatchConfig(), [])
    return engine


def age(engine, offer_id: int, days: int) -> None:
    with session(engine) as db:
        application = db.exec(select(Application).where(Application.offer_id == offer_id)).one()
        application.updated_at = TODAY - timedelta(days=days)
        db.add(application)
        db.commit()


def test_change_status_checks_transitions(engine):
    assert tracking.change_status(engine, 1, Status.TO_PREPARE) is Status.TO_REVIEW
    with pytest.raises(ValueError, match="passage interdit"):
        tracking.change_status(engine, 1, Status.SENT)
    with pytest.raises(ValueError, match="introuvable"):
        tracking.change_status(engine, 99, Status.TO_PREPARE)


def test_offer_view_shows_history_and_documents(engine, tmp_path):
    pdf = tmp_path / "cv.pdf"
    pdf.write_bytes(b"%PDF")
    tracking.change_status(engine, 1, Status.ARCHIVED, note="trop loin")
    tracking.attach_document(engine, 1, pdf, [tmp_path])
    view = tracking.offer_view(engine, 1)
    assert view.status is Status.ARCHIVED
    assert [(e.kind, e.detail) for e in view.events][1:] == [
        ("status", "archived"),
        ("note", "trop loin"),
        ("document", str(pdf.resolve())),
    ]
    with pytest.raises(ValueError, match="introuvable"):
        tracking.attach_document(engine, 1, tmp_path / "absent.pdf", [tmp_path])
    with pytest.raises(ValueError, match="hors des dossiers"):
        tracking.attach_document(engine, 1, pdf, [tmp_path / "applications"])


def test_second_follow_up_is_recorded(engine):
    send(engine, 1)
    tracking.change_status(engine, 1, Status.FOLLOWED_UP)
    assert tracking.change_status(engine, 1, Status.FOLLOWED_UP) is Status.FOLLOWED_UP


def send(engine, offer_id: int) -> None:
    for status in (Status.TO_PREPARE, Status.READY, Status.SENT):
        tracking.change_status(engine, offer_id, status)


def test_follow_up_suggests_reminders(engine):
    send(engine, 1)
    age(engine, 1, 8)
    send(engine, 2)
    age(engine, 2, 3)
    tracking.change_status(engine, 3, Status.ARCHIVED)
    items = tracking.follow_up(engine, TODAY)
    assert [(i.id, i.days) for i in items] == [(1, 8), (2, 3)]
    assert items[0].action.startswith("relancer (J+7)")
    assert items[1].action == "attendre"


def test_review_counts_answers_per_source(engine):
    since = datetime.now(UTC) - timedelta(days=1)
    send(engine, 1)
    send(engine, 2)
    tracking.change_status(engine, 2, Status.INTERVIEW)
    report = tracking.review(engine, since)
    assert (report.found, report.sent, report.answered, report.answer_rate) == (3, 2, 1, 0.5)
    assert report.sent_by_source == {"careers": 1, "francetravail": 1}
    assert report.interviews_by_source == {"francetravail": 1}


def test_cli_status_show_and_tracking(engine, tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump({"paths": {"data": str(tmp_path)}}), encoding="utf-8")
    common = ["--config", str(config)]
    runner = CliRunner()
    moved = runner.invoke(app, ["offre", "statut", "1", "to_prepare", *common])
    assert moved.exit_code == 0, moved.output
    assert "À voir puis À préparer" in moved.stdout
    refused = runner.invoke(app, ["offre", "statut", "1", "sent", *common])
    assert refused.exit_code == 1
    shown = json.loads(runner.invoke(app, ["offre", "voir", "1", *common]).stdout)
    assert shown["status"] == "to_prepare"
    listed = json.loads(runner.invoke(app, ["suivi", *common, "--json"]).stdout)
    assert {row["id"] for row in listed} == {1, 2, 3}
    review = json.loads(runner.invoke(app, ["bilan", *common, "--json"]).stdout)
    assert review["found"] == 3
