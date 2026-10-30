import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlmodel import select

from kandid_tools import scheduler
from kandid_tools.config import Config, TaskName, TasksConfig
from kandid_tools.db import TaskRun, open_db, session


class FakeRunner:
    def __init__(self, stdout: bytes = b"", returncode: int = 0, stderr: bytes = b""):
        self.calls: list[tuple[list[str], dict]] = []
        self.stdout, self.returncode, self.stderr = stdout, returncode, stderr

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, self.returncode, self.stdout, self.stderr)


@pytest.fixture
def windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(scheduler.shutil, "which", lambda name: f"C:/bin/{name}.exe")


def arguments(command: list[str]) -> dict[str, str]:
    script = command.index("-File")
    rest = command[script + 2 :]
    return dict(zip(rest[::2], rest[1::2], strict=True))


@pytest.mark.parametrize("at", ["8:30", "24:00", "08:60", "08h30", "08:30; calc"])
def test_task_hours_are_validated(at):
    with pytest.raises(ValidationError):
        TasksConfig.model_validate({"veille": {"at": at}})


def test_install_registers_enabled_tasks_and_removes_the_others(windows, tmp_path):
    config = Config.model_validate(
        {"paths": {"data": str(tmp_path)}, "tasks": {"relances": {"enabled": False, "at": "09:00"}}}
    )
    runner = FakeRunner()
    assert scheduler.install(config, runner) == [TaskName.WATCH, TaskName.DIGEST]
    calls = [arguments(command) for command, _ in runner.calls]
    assert [(c["-Action"], c["-Name"]) for c in calls] == [
        ("register", "veille"),
        ("unregister", "relances"),
        ("register", "digest"),
    ]
    watch = calls[0]
    assert watch["-At"] == "08:30"
    assert watch["-Execute"] == "C:/bin/uv.exe"
    assert watch["-Arguments"].endswith("kandid taches lancer veille")
    assert watch["-WorkingDirectory"] == str(tmp_path)
    command = runner.calls[0][0]
    assert command[0].replace("\\", "/").endswith("WindowsPowerShell/v1.0/powershell.exe")
    assert command[1] == "-NoProfile"
    assert command[command.index("-File") + 1].endswith("tasks.ps1")


def test_scheduler_errors_are_reported(windows):
    runner = FakeRunner(returncode=1, stderr=b"Access denied\r\nRegister-ScheduledTask : refus")
    with pytest.raises(scheduler.SchedulerError, match="refus"):
        scheduler.remove(runner)


def test_listed_parses_tasks(windows):
    rows = [{"name": "veille", "state": "Ready", "next": "2026-10-31T08:30:00", "last": None}]
    tasks = scheduler.listed(FakeRunner(stdout=json.dumps(rows).encode()))
    assert tasks[0].name == "veille" and tasks[0].next.startswith("2026-10-31")


def test_outside_windows_points_to_cron(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(scheduler.SchedulerError, match="cron"):
        scheduler.remove(FakeRunner())


def test_claude_command_only_allows_kandid():
    command = scheduler.claude_command(TaskName.FOLLOW_UPS, Config(), "claude")
    assert command[:3] == ["claude", "-p", "/kandid:relance"]
    options = dict(zip(command[3::2], command[4::2], strict=False))
    assert options["--permission-mode"] == "dontAsk"
    assert options["--allowedTools"] == "Bash(kandid *)"
    assert options["--max-turns"] == "30"
    assert options["--max-budget-usd"] == "0.50"
    assert "--no-session-persistence" in command


def test_run_task_files_report_log_and_run(windows, tmp_path):
    config = Config.model_validate({"paths": {"data": str(tmp_path)}})
    engine = open_db(tmp_path)
    output = {
        "subtype": "success",
        "is_error": False,
        "total_cost_usd": 0.12,
        "result": "3 offres.",
    }
    runner = FakeRunner(stdout=json.dumps(output).encode())
    run = scheduler.run_task(TaskName.WATCH, config, engine, runner)
    assert (run.ok, run.cost_usd) == (True, 0.12)
    report = tmp_path / "rapports"
    assert "3 offres." in next(report.iterdir()).read_text(encoding="utf-8")
    assert next((tmp_path / "logs").iterdir()).read_bytes().startswith(b"{")
    _, kwargs = runner.calls[0]
    assert kwargs["cwd"] == tmp_path
    assert kwargs["env"]["KANDID_HOME"] == str(tmp_path)
    with session(engine) as db:
        assert db.exec(select(TaskRun)).one().task == "veille"


def test_run_task_reports_failures(windows, tmp_path):
    config = Config.model_validate({"paths": {"data": str(tmp_path)}})
    engine = open_db(tmp_path)
    output = {"subtype": "error_max_budget_usd", "is_error": True, "result": ""}
    run = scheduler.run_task(
        TaskName.DIGEST, config, engine, FakeRunner(json.dumps(output).encode())
    )
    assert run.ok is False
    assert "error_max_budget_usd" in Path(run.report).read_text(encoding="utf-8")
    garbled = scheduler.run_task(TaskName.DIGEST, config, engine, FakeRunner(b"\xff"))
    assert garbled.ok is False
