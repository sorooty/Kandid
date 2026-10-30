import json
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from sqlmodel import col, select

from kandid_tools import bridge
from kandid_tools.bridge import Action, BridgeError, Busy, Limits, RunStatus
from kandid_tools.config import Config, WatchConfig
from kandid_tools.db import ClaudeEvent, ClaudeRun, now, open_db, session
from kandid_tools.sources.base import RawOffer
from kandid_tools.watch import add_offer

FAKE = [sys.executable, str(Path(__file__).parent / "fixtures" / "claude" / "fake_claude.py")]
LIMITS = Limits(max_turns=5, max_budget_usd=0.2)


@pytest.fixture
def config(tmp_path) -> Config:
    return Config.model_validate({"paths": {"data": str(tmp_path)}})


@pytest.fixture
def engine(tmp_path):
    engine = open_db(tmp_path)
    add_offer(engine, RawOffer(source="careers", external_id="1", company="Datavia",
                               title="Alternance data"), WatchConfig(), [])  # fmt: skip
    return engine


def events(engine, run_id: int) -> list[ClaudeEvent]:
    with session(engine) as db:
        return list(
            db.exec(
                select(ClaudeEvent)
                .where(ClaudeEvent.run_id == run_id)
                .order_by(col(ClaudeEvent.seq))
            ).all()
        )


def option(command: list[str], name: str) -> str:
    return command[command.index(name) + 1]


def test_command_is_fixed_and_offer_actions_may_edit_the_data_folder(tmp_path):
    review = bridge.command(Action.REVIEW, None, LIMITS, ["claude"], tmp_path)
    assert review[:3] == ["claude", "-p", "/kandid:bilan"]
    assert option(review, "--output-format") == "stream-json"
    assert option(review, "--permission-mode") == "dontAsk"
    assert option(review, "--permission-prompts") == "none"
    assert "--verbose" in review
    assert option(review, "--allowedTools") == "Bash(kandid *)"
    assert option(review, "--disallowedTools") == "PowerShell"
    assert "--add-dir" not in review
    apply = bridge.command(Action.APPLY, 7, LIMITS, ["claude"], tmp_path)
    assert apply[2] == "/kandid:postuler 7"
    assert option(apply, "--allowedTools") == "Bash(kandid *),Edit(./**)"
    assert option(apply, "--add-dir") == str(tmp_path)


def test_parse_line_keeps_steps_but_never_tool_output():
    stream = (Path(__file__).parent / "fixtures" / "claude" / "stream.jsonl").read_bytes()
    reduced, outcome = [], None
    for line in stream.splitlines():
        found, final = bridge.parse_line(line)
        reduced += found
        outcome = final or outcome
    assert [(e.kind, e.tool) for e in reduced] == [
        ("start", None),
        ("text", None),
        ("tool", "Bash"),
        ("tool", "Read"),
        ("tool_error", None),
        ("denied", "WebFetch"),
        ("warning", None),
        ("result", None),
    ]
    assert reduced[2].text == "kandid bilan --json"
    assert reduced[3].text == "work/12/fiche.md"
    assert all("SECRET" not in e.text for e in reduced)
    assert outcome == bridge.Outcome(ok=True, cost_usd=0.04, duration_ms=4200, turns=3)


def test_run_streams_into_the_journal(config, engine, tmp_path, monkeypatch):
    args_file = tmp_path / "args.json"
    monkeypatch.setenv("FAKE_CLAUDE_ARGS", str(args_file))
    run = bridge.run_sync(Action.REVIEW, config, engine, LIMITS, "ui", FAKE)
    assert run.status == RunStatus.OK
    assert (run.cost_usd, run.duration_ms, run.turns) == (0.04, 4200, 3)
    assert [e.seq for e in events(engine, run.id)] == list(range(8))
    assert bridge.final_text(engine, run.id).startswith("2 candidatures")
    received = json.loads(args_file.read_text(encoding="utf-8"))
    assert Path(received["cwd"]) == tmp_path
    assert received["home"] == str(tmp_path)
    log = next((tmp_path / "logs").iterdir())
    assert log.read_bytes().count(b"\n") == 8


def test_run_without_result_is_an_error(config, engine, tmp_path, monkeypatch):
    stream = tmp_path / "short.jsonl"
    stream.write_text('{"type":"system","subtype":"init","model":"m"}\n', encoding="utf-8")
    monkeypatch.setenv("FAKE_CLAUDE_STREAM", str(stream))
    monkeypatch.setenv("FAKE_CLAUDE_EXIT", "1")
    run = bridge.run_sync(Action.DIGEST, config, engine, LIMITS, "digest", FAKE)
    assert run.status == RunStatus.ERROR
    assert "code 1" in bridge.final_text(engine, run.id)


def test_missing_binary_is_recorded(config, engine, monkeypatch):
    monkeypatch.setattr(bridge.shutil, "which", lambda name: None)
    run = bridge.run_sync(Action.WATCH, config, engine, LIMITS, "veille")
    assert run.status == RunStatus.ERROR
    assert bridge.final_text(engine, run.id) == "Claude Code introuvable (commande claude)"


def test_offer_actions_need_an_existing_offer(config, engine):
    with pytest.raises(BridgeError, match="requis"):
        bridge.start(Action.APPLY, None, config, engine, LIMITS, claude=FAKE)
    with pytest.raises(BridgeError, match="inattendu"):
        bridge.start(Action.REVIEW, 1, config, engine, LIMITS, claude=FAKE)
    with pytest.raises(BridgeError, match="introuvable"):
        bridge.start(Action.APPLY, 99, config, engine, LIMITS, claude=FAKE)


def test_one_run_at_a_time_and_stop(config, engine, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_SLEEP", "30")
    run, thread = bridge.start(Action.APPLY, 1, config, engine, LIMITS, claude=FAKE)
    try:
        with pytest.raises(Busy):
            bridge.start(Action.REVIEW, None, config, engine, LIMITS, claude=FAKE)
        assert bridge.stop(run.id + 1) is False
        assert bridge.stop(run.id) is True
    finally:
        thread.join(timeout=20)
    assert not thread.is_alive()
    with session(engine) as db:
        assert db.get(ClaudeRun, run.id).status == RunStatus.STOPPED
    # The slot is free again.
    monkeypatch.delenv("FAKE_CLAUDE_SLEEP")
    assert bridge.run_sync(Action.REVIEW, config, engine, LIMITS, "ui", FAKE).status == "ok"


def test_mark_interrupted_spares_a_recent_scheduled_run(engine):
    with session(engine) as db:
        db.add(ClaudeRun(action="bilan", origin="ui"))
        db.add(ClaudeRun(action="veille", origin="veille"))
        db.add(ClaudeRun(action="digest", origin="digest", started_at=now() - timedelta(hours=2)))
        db.commit()
    assert bridge.mark_interrupted(engine) == 2
    with session(engine) as db:
        statuses = {r.origin: r.status for r in db.exec(select(ClaudeRun)).all()}
    assert statuses == {"ui": "interrupted", "veille": "running", "digest": "interrupted"}


def test_plugin_dir_is_absolute(tmp_path, monkeypatch):
    # Claude runs from the data folder: a relative plugin path would point inside it.
    monkeypatch.chdir(tmp_path)
    argv = bridge.command(Action.REVIEW, None, LIMITS, ["claude"], tmp_path, Path("."))
    assert option(argv, "--plugin-dir") == str(tmp_path.resolve())
