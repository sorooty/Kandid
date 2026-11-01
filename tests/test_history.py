import json

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from kandid_tools import tracking
from kandid_tools.cli import app
from kandid_tools.db import open_db
from kandid_tools.history import PastApplication, import_history
from kandid_tools.status import Status

PAST = [
    {"company": "Nordlys", "title": "Alternance Data Scientist", "status": "sent",
     "sent_on": "2026-10-20", "url": "https://exemple.fr/offres/1", "contract": "alternance",
     "contact": "Recruteuse Nordlys", "notes": "Relancer fin octobre"},
    {"company": "Datavia", "title": "Data Analyst", "status": "Refus", "sent_on": "2026-10-09"},
    {"company": "Maison Tisserand", "title": "Alternance BI", "status": "ready"},
]  # fmt: skip


def test_import_creates_dated_history_and_is_idempotent(tmp_path):
    engine = open_db(tmp_path)
    items = [PastApplication.model_validate(row) for row in PAST]
    report = import_history(engine, items)
    assert report.added == [1, 2, 3]
    view = tracking.offer_view(engine, 1)
    assert view.status is Status.SENT
    assert view.events[0].at.date().isoformat() == "2026-10-20"
    assert [e.detail for e in view.events][2:] == ["contact : Recruteuse Nordlys",
                                                   "Relancer fin octobre"]  # fmt: skip
    # The French label written by hand is understood.
    assert tracking.offer_view(engine, 2).status is Status.REJECTED
    again = import_history(engine, items)
    assert (again.added, len(again.skipped)) == ([], 3)


def test_unknown_status_is_rejected():
    with pytest.raises(ValidationError):
        PastApplication.model_validate(
            {"company": "Nordlys", "title": "Data", "status": "peut-être"}
        )


def test_cli_import(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(f"paths:\n  data: {tmp_path.as_posix()}\n", encoding="utf-8")
    history = tmp_path / "historique.json"
    history.write_text(json.dumps(PAST), encoding="utf-8")
    runner = CliRunner()
    first = runner.invoke(app, ["historique", str(history), "--config", str(config)])
    assert first.exit_code == 0, first.output
    assert "3 candidatures importées" in first.output
    second = runner.invoke(app, ["historique", str(history), "--config", str(config), "--json"])
    assert json.loads(second.output)["added"] == []


def test_schema_version_is_set(tmp_path):
    engine = open_db(tmp_path)
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA user_version").scalar() == 1
