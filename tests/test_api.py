import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kandid_api.app import create_app
from kandid_tools.config import Config, WatchConfig
from kandid_tools.db import ClaudeRun, open_db, session
from kandid_tools.sources.base import RawOffer
from kandid_tools.watch import add_offer

FAKE = [sys.executable, str(Path(__file__).parent / "fixtures" / "claude" / "fake_claude.py")]
BASE = "http://127.0.0.1:8765"
FORM = "application/x-www-form-urlencoded"


@pytest.fixture
def client(tmp_path):
    engine = open_db(tmp_path)
    for n in range(1, 4):
        offer = RawOffer(
            source="careers", external_id=str(n), company=f"Société {n}", title="Poste"
        )
        add_offer(engine, offer, WatchConfig(), [])
    with session(engine) as db:
        db.add(ClaudeRun(action="bilan", origin="ui"))
        db.commit()
    config = Config.model_validate({"paths": {"data": str(tmp_path)}})
    with TestClient(create_app(config, engine, FAKE), base_url=BASE) as client:
        yield client


def sse(text: str) -> list[dict]:
    """Events of an SSE body, keepalive comments left out."""
    events = []
    for block in text.strip().split("\n\n"):
        fields = dict(
            line.split(": ", 1) for line in block.splitlines() if not line.startswith(":")
        )
        if fields:
            events.append(fields)
    return events


def test_startup_closes_runs_left_running(client):
    assert client.get("/api/runs/1").json()["status"] == "interrupted"


def test_statuses_list_columns_and_moves(client):
    columns = {c["value"]: c for c in client.get("/api/statuts").json()}
    assert columns["to_review"]["label"] == "À voir"
    assert columns["to_review"]["next"] == ["to_prepare", "archived"]
    assert columns["archived"]["next"] == []


def test_offers_are_paginated_and_filtered(client):
    page = client.get("/api/offres", params={"limit": 2, "offset": 1}).json()
    assert [o["id"] for o in page] == [2, 1]
    assert client.get("/api/offres", params={"statut": "ready"}).json() == []
    assert client.get("/api/offres", params={"limit": 0}).status_code == 422


def test_offer_sheet_and_status_moves(client):
    assert client.get("/api/offres/1").json()["company"] == "Société 1"
    assert client.get("/api/offres/99").status_code == 404
    moved = client.post(
        "/api/offres/1/statut", json={"statut": "to_prepare", "note": "intéressant"}
    )
    assert moved.json()["status"] == "to_prepare"
    assert [e["kind"] for e in moved.json()["events"]][-2:] == ["status", "note"]
    forbidden = client.post("/api/offres/1/statut", json={"statut": "offer"})
    assert forbidden.status_code == 409
    assert "passage interdit" in forbidden.json()["detail"]
    assert client.post("/api/offres/99/statut", json={"statut": "ready"}).status_code == 404


def test_follow_up_review_and_tasks(client):
    assert len(client.get("/api/suivi").json()) == 3
    assert client.get("/api/bilan", params={"jours": 30}).json()["found"] == 3
    tasks = client.get("/api/taches").json()
    assert [(t["name"], t["at"], t["last_run"]) for t in tasks] == [
        ("veille", "08:30", None),
        ("relances", "09:00", None),
        ("digest", "19:00", None),
    ]


def test_run_starts_and_streams_its_events(client):
    started = client.post("/api/runs", json={"action": "bilan"})
    assert started.status_code == 202
    run_id = started.json()["id"]
    events = sse(client.get(f"/api/runs/{run_id}/events").text)
    assert [e["event"] for e in events] == [
        "start", "text", "tool", "tool", "tool_error", "denied", "warning", "result", "end",
    ]  # fmt: skip
    assert "SECRET" not in json.dumps(events)
    assert json.loads(events[-1]["data"])["status"] == "ok"
    assert client.get(f"/api/runs/{run_id}").json()["cost_usd"] == 0.04
    assert client.get("/api/runs", params={"limit": 1}).json()[0]["id"] == run_id
    # A browser reconnecting gets only what it missed.
    resumed = sse(client.get(f"/api/runs/{run_id}/events", headers={"Last-Event-ID": "6"}).text)
    assert [e["event"] for e in resumed] == ["result", "end"]


def test_run_requests_are_validated(client):
    assert client.post("/api/runs", json={"action": "rm -rf"}).status_code == 422
    assert client.post("/api/runs", json={"action": "postuler"}).status_code == 400
    assert client.post("/api/runs", json={"action": "postuler", "offer_id": 99}).status_code == 400
    assert client.get("/api/runs/99").status_code == 404
    assert client.get("/api/runs/99/events").status_code == 404
    assert client.post("/api/runs/1/stop", json={}).json() == {"stopped": False}


@pytest.mark.parametrize(
    ("method", "path", "kwargs", "code"),
    [
        ("get", "/api/offres", {"headers": {"Host": "evil.example"}}, 400),
        ("post", "/api/runs", {"content": "action=bilan", "headers": {"Content-Type": FORM}}, 415),
        ("post", "/api/runs", {"json": {"action": "bilan"},
                               "headers": {"Origin": "http://evil.example"}}, 403),
    ],
)  # fmt: skip
def test_only_the_local_browser_is_served(client, method, path, kwargs, code):
    assert getattr(client, method)(path, **kwargs).status_code == code


def test_same_origin_post_is_accepted(client):
    response = client.post(
        "/api/offres/2/statut", json={"statut": "to_prepare"}, headers={"Origin": BASE}
    )
    assert response.status_code == 200
