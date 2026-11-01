import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from kandid_tools.hooks import Hook, run

from conftest import CAMILLE

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def data(monkeypatch, tmp_path):
    """A data folder with Camille's profile and a master folder beside it."""
    home = tmp_path / "kandid"
    master = tmp_path / "Mon CV" / "00_MASTER"
    master.mkdir(parents=True)
    home.mkdir()
    shutil.copy(CAMILLE / "profile.yaml", home / "profile.yaml")
    config = {"paths": {"data": str(home), "master": str(master)}}
    (home / "config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setenv("KANDID_HOME", str(home))
    return home, master


def answer(hook: Hook, payload: dict) -> dict | None:
    out = run(hook, json.dumps(payload))
    return json.loads(out) if out else None


def decision(result: dict | None) -> str | None:
    return result["hookSpecificOutput"]["permissionDecision"] if result else None


@pytest.mark.parametrize(
    ("tool", "relative", "expected"),
    [
        ("Write", "cv.tex", "deny"),
        ("Edit", "sub/../cv.tex", "deny"),
        ("NotebookEdit", "notes.ipynb", "deny"),
        ("Write", "../autre.tex", None),
        ("Read", "cv.tex", None),
    ],
)
def test_protect_master_on_file_tools(data, tool, relative, expected):
    _, master = data
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    payload = {"tool_name": tool, "tool_input": {key: str(master / relative)}}
    assert decision(answer(Hook.PROTECT_MASTER, payload)) == expected


def test_protect_master_resolves_relative_paths_and_case(data):
    _, master = data
    payload = {
        "tool_name": "Write",
        "cwd": str(master.parent),
        "tool_input": {"file_path": "00_master/x.tex"},
    }
    expected = "deny" if master.parent.joinpath("00_master").exists() else None
    assert decision(answer(Hook.PROTECT_MASTER, payload)) == expected


def test_protect_master_asks_for_shell_commands_naming_it(data):
    _, master = data
    command = f'rm "{str(master).replace("/", chr(92))}\\cv.tex"'
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    assert decision(answer(Hook.PROTECT_MASTER, payload)) == "ask"
    other = {"tool_name": "Bash", "tool_input": {"command": "ls"}}
    assert answer(Hook.PROTECT_MASTER, other) is None


def test_no_master_configured_means_no_opinion(monkeypatch, tmp_path):
    monkeypatch.setenv("KANDID_HOME", str(tmp_path))
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(tmp_path / "x")}}
    assert answer(Hook.PROTECT_MASTER, payload) is None


@pytest.mark.parametrize(
    ("tool", "expected"),
    [
        ("mcp__claude_ai_Gmail__send_message", "ask"),
        ("mcp__claude_ai_Gmail__reply", "ask"),
        ("mcp__outlook__forward_mail", "ask"),
        ("mcp__claude_ai_Gmail__create_draft", None),
        ("Bash", None),
    ],
)
def test_confirm_send(data, tool, expected):
    assert decision(answer(Hook.CONFIRM_SEND, {"tool_name": tool, "tool_input": {}})) == expected


def test_broken_config_asks_instead_of_letting_through(monkeypatch, tmp_path):
    (tmp_path / "config.yaml").write_text("paths: [", encoding="utf-8")
    monkeypatch.setenv("KANDID_HOME", str(tmp_path))
    payload = {"tool_name": "Write", "tool_input": {"file_path": "x"}}
    result = answer(Hook.PROTECT_MASTER, payload)
    assert decision(result) == "ask"
    assert "paths" not in result["hookSpecificOutput"]["permissionDecisionReason"]


def test_check_document_blocks_unknown_skill(data):
    home, _ = data
    tex = home / "applications" / "CV" / "CV_Camille_Martin_Acme.tex"
    tex.parent.mkdir(parents=True)
    tex.write_text(r"\section{Compétences} Python, SQL, Kubernetes", encoding="utf-8")
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(tex)}}
    result = answer(Hook.CHECK_DOCUMENT, payload)
    assert result["decision"] == "block"
    assert "Kubernetes" in result["reason"]

    tex.write_text(r"\section{Compétences} Python, SQL", encoding="utf-8")
    assert answer(Hook.CHECK_DOCUMENT, payload) is None


def test_check_document_ignores_other_files(data):
    home, _ = data
    elsewhere = home.parent / "notes.tex"
    elsewhere.write_text("Kubernetes", encoding="utf-8")
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(elsewhere)}}
    assert answer(Hook.CHECK_DOCUMENT, payload) is None


def test_module_entry_point_reads_stdin(data):
    _, master = data
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(master / "é.tex")}})
    result = subprocess.run(
        [sys.executable, "-m", "kandid_tools.hooks", "protect-master"],
        input=payload.encode("utf-8"),
        capture_output=True,
        check=True,
    )
    answer = json.loads(result.stdout.decode("utf-8"))
    assert answer["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows path spellings")
def test_protect_master_sees_through_long_path_prefix(data):
    _, master = data
    payload = {"tool_name": "Write", "tool_input": {"file_path": "\\\\?\\" + str(master / "q.tex")}}
    assert decision(answer(Hook.PROTECT_MASTER, payload)) == "deny"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows path spellings")
def test_protect_master_asks_for_other_shell_spellings(data, monkeypatch):
    _, master = data
    monkeypatch.setenv("USERPROFILE", str(master.parent.parent))
    monkeypatch.setenv("HOME", str(master.parent.parent))
    posix = master.as_posix()
    git_bash = f"/{posix[0].lower()}{posix[2:]}"
    for command in (f"rm '{git_bash}/cv.tex'", 'rm "$HOME/Mon CV/00_MASTER/cv.tex"'):
        payload = {"tool_name": "Bash", "tool_input": {"command": command}}
        assert decision(answer(Hook.PROTECT_MASTER, payload)) == "ask", command
    inside = {"tool_name": "Bash", "cwd": str(master), "tool_input": {"command": "rm cv.tex"}}
    assert decision(answer(Hook.PROTECT_MASTER, inside)) == "ask"


@pytest.mark.parametrize(
    ("tool", "expected"),
    [
        ("mcp__mail__SendEmail", "ask"),
        ("mcp__claude_ai_Google_Drive__share_file", "ask"),
        ("mcp__claude_ai_Google_Calendar__create_event", "ask"),
        ("mcp__claude_ai_Google_Calendar__respond_to_event", "ask"),
        ("mcp__claude_ai_Google_Calendar__get_event", None),
    ],
)
def test_confirm_send_covers_other_ways_to_reach_someone(data, tool, expected):
    assert decision(answer(Hook.CONFIRM_SEND, {"tool_name": tool, "tool_input": {}})) == expected


def test_confirm_send_matcher_reaches_the_hook():
    hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    matcher = next(
        entry["matcher"]
        for entry in hooks["hooks"]["PreToolUse"]
        if entry["hooks"][0]["args"][-1] == Hook.CONFIRM_SEND
    )
    for tool in ("mcp__mail__SendEmail", "mcp__claude_ai_Gmail__send_message", "mcp__x__shareFile"):
        assert re.search(matcher, tool), tool


def test_invalid_payload_asks(data):
    result = run(Hook.PROTECT_MASTER, b"\xff\xfe")
    assert json.loads(result)["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_hook_ignores_modules_planted_in_the_working_folder(data, tmp_path):
    _, master = data
    planted = tmp_path / "workspace" / "kandid_tools"
    planted.mkdir(parents=True)
    (planted / "__init__.py").write_text("", encoding="utf-8")
    (planted / "hooks.py").write_text('print("{}")', encoding="utf-8")
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(master / "x.tex")}})
    result = subprocess.run(
        [sys.executable, "-I", "-m", "kandid_tools.hooks", "protect-master"],
        input=payload.encode("utf-8"),
        capture_output=True,
        check=True,
        cwd=planted.parent,
    )
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
