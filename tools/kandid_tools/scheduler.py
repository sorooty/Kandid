"""Scheduled tasks: Windows Task Scheduler entries that run `kandid taches lancer <task>`, which
runs one Kandid command through `claude -p` and files its report.

A task prepares only. `claude -p` runs in `dontAsk` mode: anything not pre-allowed (only `kandid`
commands) is refused, so a task cannot send, browse or write outside what `kandid` writes.
"""

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime
from importlib.resources import files
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import Engine

from kandid_tools.bridge import Action, Limits, RunStatus, final_text, run_sync
from kandid_tools.config import Config, TaskName
from kandid_tools.db import ClaudeRun, session

REPORTS_DIR = "rapports"
ACTIONS = {
    TaskName.WATCH: Action.WATCH,
    TaskName.FOLLOW_UPS: Action.FOLLOW_UPS,
    TaskName.DIGEST: Action.DIGEST,
}
Runner = Callable[..., subprocess.CompletedProcess[bytes]]


class SchedulerError(RuntimeError):
    pass


class ScheduledTask(BaseModel):
    name: str
    state: str
    next: str | None = None
    last: str | None = None


def plugin_root() -> Path:
    """The plugin folder this package runs from: `uv run --project` installs it in editable mode."""
    root = Path(__file__).resolve().parents[2]
    if not (root / ".claude-plugin").is_dir():
        raise SchedulerError(
            "dossier du plugin introuvable : lance la commande depuis le plugin Kandid"
        )
    return root


def task_command(root: Path) -> list[str]:
    """What the scheduler runs, minus the task name."""
    uv = shutil.which("uv")
    if uv is None:
        raise SchedulerError("uv introuvable : il est nécessaire aux tâches planifiées")
    return [
        uv,
        "run",
        "--quiet",
        "--frozen",
        "--no-dev",
        "--project",
        str(root),
        "kandid",
        "taches",
        "lancer",
    ]


def _powershell(runner: Runner, *args: str) -> str:
    if sys.platform != "win32":
        raise SchedulerError(
            "le Planificateur de tâches n'existe que sous Windows : voir A_SAVOIR.md pour cron"
        )
    script = files("kandid_tools") / "data" / "tasks.ps1"
    # Bypass applies to this one process and this one script, shipped with Kandid: the user's
    # policy may otherwise refuse unsigned local scripts.
    # Windows PowerShell ships with every Windows and has the ScheduledTasks module; the full path
    # avoids depending on PATH, which differs in Git Bash and in the scheduler.
    system_root = Path(os.environ.get("SYSTEMROOT", r"C:\Windows"))
    powershell = system_root / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    command = [
        str(powershell),
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        *args,
    ]
    try:
        result = runner(command, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SchedulerError(f"PowerShell n'a pas pu être lancé ({type(error).__name__})") from None
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip().splitlines()
        raise SchedulerError(f"Planificateur de tâches : {detail[-1] if detail else 'échec'}")
    return result.stdout.decode("utf-8", errors="replace")


def install(config: Config, runner: Runner = subprocess.run) -> list[TaskName]:
    """Register the enabled tasks and remove the disabled ones: the scheduler matches the config."""
    command = task_command(plugin_root())
    installed = []
    for task in TaskName:
        settings = config.tasks.settings(task)
        if not settings.enabled:
            _powershell(runner, "-Action", "unregister", "-Name", task.value)
            continue
        _powershell(
            runner,
            "-Action",
            "register",
            "-Name",
            task.value,
            "-At",
            settings.at,
            "-Execute",
            command[0],
            "-Arguments",
            subprocess.list2cmdline([*command[1:], task.value]),
            "-WorkingDirectory",
            str(config.paths.data),
        )
        installed.append(task)
    return installed


def remove(runner: Runner = subprocess.run) -> None:
    _powershell(runner, "-Action", "unregister")


def listed(runner: Runner = subprocess.run) -> list[ScheduledTask]:
    output = _powershell(runner, "-Action", "list").strip()
    return [ScheduledTask.model_validate(row) for row in json.loads(output or "[]")]


def run_task(
    task: TaskName,
    config: Config,
    engine: Engine,
    claude: list[str] | None = None,
    plugin_dir: Path | None = None,
) -> ClaudeRun:
    """Run one task now through the bridge; its report goes to `<data>/rapports`."""
    limits = Limits(max_turns=config.tasks.max_turns, max_budget_usd=config.tasks.max_budget_usd)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    run = run_sync(ACTIONS[task], config, engine, limits, task.value, claude, plugin_dir)
    assert run.id is not None
    report_path = config.paths.data / REPORTS_DIR / f"{stamp}_{task.value}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    text = final_text(engine, run.id)
    if run.status != RunStatus.OK:
        text = f"La tâche s'est arrêtée ({run.status}).\n\n{text}".strip()
    report_path.write_text(f"# {task.value}, {stamp}\n\n{text}\n", encoding="utf-8")
    with session(engine) as db:
        run.report = str(report_path)
        db.add(run)
        db.commit()
    return run
