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

from kandid_tools.config import Config, TaskName
from kandid_tools.db import TaskRun, now, session

REPORTS_DIR = "rapports"
LOGS_DIR = "logs"
SKILLS = {
    TaskName.WATCH: "/kandid:veille",
    TaskName.FOLLOW_UPS: "/kandid:relance",
    TaskName.DIGEST: "/kandid:digest",
}
# Appended to Claude's system prompt: nobody is there to answer a question during a scheduled run.
UNATTENDED = (
    "This is a scheduled run: nobody is at the keyboard. Do not ask questions and do not wait "
    "for a confirmation; prepare only. Your final answer is the report the user reads later: "
    "short, in French, with what was found and what they should do next."
)
RUN_TIMEOUT_S = 30 * 60
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


def claude_command(
    task: TaskName, config: Config, claude: str, plugin_dir: Path | None = None
) -> list[str]:
    # An installed plugin is found by Claude Code itself; `plugin_dir` loads a local copy instead.
    plugin = ["--plugin-dir", str(plugin_dir)] if plugin_dir else []
    return [
        claude,
        *plugin,
        "-p",
        SKILLS[task],
        "--permission-mode",
        "dontAsk",
        "--allowedTools",
        "Bash(kandid *)",
        "--max-turns",
        str(config.tasks.max_turns),
        "--max-budget-usd",
        f"{config.tasks.max_budget_usd:.2f}",
        "--output-format",
        "json",
        "--no-session-persistence",
        "--append-system-prompt",
        UNATTENDED,
    ]


def _report(output: bytes) -> tuple[bool, float | None, str]:
    """Success, cost and the text of Claude's final answer, from `--output-format json`."""
    try:
        result = json.loads(output.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False, None, "Réponse de Claude illisible : voir le journal."
    if not isinstance(result, dict):
        return False, None, "Réponse de Claude illisible : voir le journal."
    cost = result.get("total_cost_usd")
    text = str(result.get("result") or "")
    ok = not result.get("is_error") and result.get("subtype") == "success"
    if not ok:
        text = f"La tâche s'est arrêtée ({result.get('subtype', 'erreur')}).\n\n{text}".strip()
    return ok, cost if isinstance(cost, int | float) else None, text


def run_task(
    task: TaskName,
    config: Config,
    engine: Engine,
    runner: Runner = subprocess.run,
    plugin_dir: Path | None = None,
) -> TaskRun:
    """Run one task now; its report goes to `<data>/rapports`, its raw output to `<data>/logs`."""
    data = config.paths.data
    started = now()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    report_path = data / REPORTS_DIR / f"{stamp}_{task.value}.md"
    log_path = data / LOGS_DIR / f"{stamp}_{task.value}.json"
    claude = shutil.which("claude")
    if claude is None:
        ok, cost, text, raw = False, None, "Claude Code introuvable (commande claude).", b""
    else:
        # The child's `kandid` calls must find this data folder, whatever the scheduler's env.
        env = {**os.environ, "KANDID_HOME": str(data)}
        try:
            result = runner(
                claude_command(task, config, claude, plugin_dir),
                cwd=data,
                env=env,
                capture_output=True,
                timeout=RUN_TIMEOUT_S,
            )
            ok, cost, text = _report(result.stdout)
            raw = result.stdout + b"\n" + result.stderr
        except subprocess.TimeoutExpired:
            ok, cost, text, raw = False, None, "La tâche a dépassé 30 minutes.", b""
    for path in (report_path, log_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(f"# {task.value}, {stamp}\n\n{text}\n", encoding="utf-8")
    log_path.write_bytes(raw)
    run = TaskRun(
        task=task.value,
        started_at=started,
        finished_at=now(),
        ok=ok,
        cost_usd=cost,
        report=str(report_path),
    )
    with session(engine) as db:
        db.add(run)
        db.commit()
    return run
