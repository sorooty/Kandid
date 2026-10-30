"""Runs one Kandid command through `claude -p` and journals its steps in SQLite as they come.

Used by the CRM (a button starts a run, the page follows it live) and by the scheduled tasks.
Only fixed actions run, with at most an offer number as argument: no text from a request ever
reaches the prompt or the command line. `dontAsk` refuses any tool not allowed below, so a run
cannot send, browse or write outside the data folder.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import Engine
from sqlmodel import col, or_, select

from kandid_tools.config import Config
from kandid_tools.db import ClaudeEvent, ClaudeRun, Offer, now, session

LOGS_DIR = "logs"
RUN_TIMEOUT_S = 30 * 60
# A journal line shows what Claude did, not a whole file it wrote or read.
TEXT_LIMIT = 4000
TOOL_LIMIT = 200
# Appended to Claude's system prompt: nobody answers questions during a run.
UNATTENDED = (
    "This run is unattended: nobody can answer a question or confirm a step. Do not ask; "
    "prepare only, and stop where a decision belongs to the user. Your final answer is the "
    "report the user reads: short, in French, with what was done and what they should do next."
)


class Action(StrEnum):
    WATCH = "veille"
    FOLLOW_UPS = "relance"
    DIGEST = "digest"
    REVIEW = "bilan"
    APPLY = "postuler"
    CV = "cv"
    LETTER = "lm"
    INTERVIEW = "prep-entretien"


# Actions on one offer: they take its number and write their working files in the data folder.
OFFER_ACTIONS = frozenset({Action.APPLY, Action.CV, Action.LETTER, Action.INTERVIEW})


class RunStatus(StrEnum):
    RUNNING = "running"
    OK = "ok"
    ERROR = "error"
    STOPPED = "stopped"
    INTERRUPTED = "interrupted"


class BridgeError(RuntimeError):
    pass


class Busy(BridgeError):
    pass


class Limits(BaseModel):
    max_turns: int
    max_budget_usd: float


class Reduced(BaseModel):
    """What the journal keeps of one stream message."""

    kind: str
    text: str = ""
    tool: str | None = None


class Outcome(BaseModel):
    ok: bool = False
    cost_usd: float | None = None
    duration_ms: int | None = None
    turns: int | None = None


class _Loose(BaseModel):
    model_config = ConfigDict(extra="ignore")


class _Block(_Loose):
    type: str
    text: str | None = None
    name: str | None = None
    input: dict[str, Any] | None = None
    is_error: bool | None = None


class _Message(_Loose):
    content: list[_Block] | str = []


class _Line(_Loose):
    type: str
    subtype: str | None = None
    model: str | None = None
    # A conversation message, or plain text on system events such as `permission_denied`.
    message: _Message | str | None = None
    tool_name: str | None = None
    is_error: bool | None = None
    result: str | None = None
    total_cost_usd: float | None = None
    duration_ms: int | None = None
    num_turns: int | None = None


def command(
    action: Action,
    offer_id: int | None,
    limits: Limits,
    claude: list[str],
    applications: Path,
    plugin_dir: Path | None = None,
) -> list[str]:
    prompt = f"/kandid:{action.value}" + (f" {offer_id}" if offer_id is not None else "")
    tools = ["Bash(kandid *)"]
    extra: list[str] = []
    if action in OFFER_ACTIONS:
        # `./**` is the working folder, i.e. the data folder; Edit rules cover Write too.
        tools.append("Edit(./**)")
        extra = ["--add-dir", str(applications)]
    # An installed plugin is found by Claude Code itself; `plugin_dir` loads a local copy instead.
    # Absolute, since Claude runs from the data folder, not from where `kandid` was called.
    plugin = ["--plugin-dir", str(plugin_dir.resolve())] if plugin_dir else []
    return [
        *claude,
        *plugin,
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--permission-mode",
        "dontAsk",
        "--permission-prompts",
        "none",
        "--allowedTools",
        ",".join(tools),
        *extra,
        "--max-turns",
        str(limits.max_turns),
        "--max-budget-usd",
        f"{limits.max_budget_usd:.2f}",
        "--no-session-persistence",
        "--append-system-prompt",
        UNATTENDED,
    ]


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _tool_summary(block: _Block) -> str:
    """The part of a tool call worth showing: a command's first line, a path, a subagent."""
    for key in ("command", "file_path", "description", "skill", "url", "pattern"):
        value = (block.input or {}).get(key)
        if isinstance(value, str) and value.strip():
            return _clip(value.strip().splitlines()[0], TOOL_LIMIT)
    return ""


def parse_line(raw: bytes) -> tuple[list[Reduced], Outcome | None]:
    """Journal entries for one stream line, and the outcome when it is the final result."""
    try:
        line = _Line.model_validate(json.loads(raw.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError):
        text = raw.decode("utf-8", errors="replace").strip()
        return ([Reduced(kind="warning", text=_clip(text, TOOL_LIMIT))] if text else []), None
    if line.type == "system" and line.subtype == "init":
        return [Reduced(kind="start", text=line.model or "")], None
    if line.type == "system" and line.subtype == "permission_denied":
        return [Reduced(kind="denied", tool=line.tool_name)], None
    if line.type == "result":
        outcome = Outcome(
            ok=line.subtype == "success" and not line.is_error,
            cost_usd=line.total_cost_usd,
            duration_ms=line.duration_ms,
            turns=line.num_turns,
        )
        text = line.result or f"Run arrêté ({line.subtype or 'erreur'})."
        return [Reduced(kind="result", text=_clip(text, TEXT_LIMIT))], outcome
    content = line.message.content if isinstance(line.message, _Message) else None
    blocks = content if isinstance(content, list) else []
    events: list[Reduced] = []
    for block in blocks:
        if line.type == "assistant" and block.type == "text" and block.text and block.text.strip():
            events.append(Reduced(kind="text", text=_clip(block.text.strip(), TEXT_LIMIT)))
        elif line.type == "assistant" and block.type == "tool_use":
            events.append(Reduced(kind="tool", tool=block.name, text=_tool_summary(block)))
        elif line.type == "user" and block.type == "tool_result" and block.is_error:
            # The output itself stays out of the journal: it may be CV or profile text.
            events.append(Reduced(kind="tool_error"))
    return events, None


class _Runs:
    """The single run in progress: two runs at once would compete for the quota and the files."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.process: subprocess.Popen[bytes] | None = None
        self.run_id: int | None = None
        self.stopped = False


_runs = _Runs()


def claude_binary() -> list[str]:
    claude = shutil.which("claude")
    if claude is None:
        raise BridgeError("Claude Code introuvable (commande claude)")
    return [claude]


def _add_events(engine: Engine, run_id: int, start: int, events: list[Reduced]) -> int:
    if not events:
        return start
    with session(engine) as db:
        for offset, event in enumerate(events):
            db.add(ClaudeEvent(run_id=run_id, seq=start + offset, **event.model_dump()))
        db.commit()
    return start + len(events)


def _finish(engine: Engine, run_id: int, status: RunStatus, outcome: Outcome) -> ClaudeRun:
    with session(engine) as db:
        run = db.get(ClaudeRun, run_id)
        if run is None:
            raise BridgeError(f"run {run_id} introuvable")
        run.status = status
        run.finished_at = now()
        run.cost_usd = outcome.cost_usd
        run.duration_ms = outcome.duration_ms
        run.turns = outcome.turns
        db.add(run)
        db.commit()
        return run


def _pump(engine: Engine, run_id: int, process: subprocess.Popen[bytes], log_path: Path) -> None:
    seq, outcome = 0, None
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timer = threading.Timer(RUN_TIMEOUT_S, _kill, args=(process,))
    timer.start()
    try:
        with log_path.open("wb") as log:
            assert process.stdout is not None
            for raw in process.stdout:
                log.write(raw)
                events, final = parse_line(raw)
                outcome = final or outcome
                seq = _add_events(engine, run_id, seq, events)
        code = process.wait()
    finally:
        timer.cancel()
    with _runs.lock:
        stopped = _runs.stopped
        _runs.process, _runs.run_id, _runs.stopped = None, None, False
    if stopped:
        status = RunStatus.STOPPED
    elif outcome is not None and outcome.ok and code == 0:
        status = RunStatus.OK
    else:
        status = RunStatus.ERROR
        if outcome is None:
            reason = "délai de 30 minutes dépassé" if code is None or code < 0 else f"code {code}"
            _add_events(
                engine, run_id, seq, [Reduced(kind="error", text=f"Run interrompu ({reason}).")]
            )
    _finish(engine, run_id, status, outcome or Outcome())


def _kill(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        # TerminateProcess would leave Claude's own children (shells running `kandid`) behind.
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True, check=False
        )
    else:
        process.terminate()


def start(
    action: Action,
    offer_id: int | None,
    config: Config,
    engine: Engine,
    limits: Limits,
    origin: str = "ui",
    claude: list[str] | None = None,
    plugin_dir: Path | None = None,
) -> tuple[ClaudeRun, threading.Thread | None]:
    """Start a run in the background; the thread is None when it failed before starting."""
    if (action in OFFER_ACTIONS) != (offer_id is not None):
        raise BridgeError(
            f"{action.value} : numéro d'offre {'requis' if offer_id is None else 'inattendu'}"
        )
    if offer_id is not None:
        with session(engine) as db:
            if db.get(Offer, offer_id) is None:
                raise BridgeError(f"offre {offer_id} introuvable")
    data = config.paths.data
    with _runs.lock:
        if _runs.process is not None:
            raise Busy("un run est déjà en cours : attends sa fin ou arrête-le")
        with session(engine) as db:
            run = ClaudeRun(action=action.value, offer_id=offer_id, origin=origin)
            db.add(run)
            db.commit()
        assert run.id is not None
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        log_path = data / LOGS_DIR / f"{stamp}_{run.id}_{action.value}.jsonl"
        try:
            argv = command(
                action,
                offer_id,
                limits,
                claude or claude_binary(),
                config.paths.applications_dir,
                plugin_dir,
            )
            # The child's `kandid` calls must find this data folder, whatever the caller's env.
            process = subprocess.Popen(
                argv,
                cwd=data,
                env={**os.environ, "KANDID_HOME": str(data)},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        except (BridgeError, OSError) as error:
            message = str(error) if isinstance(error, BridgeError) else "Claude n'a pas pu démarrer"
            _add_events(engine, run.id, 0, [Reduced(kind="error", text=message)])
            return _finish(engine, run.id, RunStatus.ERROR, Outcome()), None
        _runs.process, _runs.run_id, _runs.stopped = process, run.id, False
    thread = threading.Thread(target=_pump, args=(engine, run.id, process, log_path), daemon=True)
    thread.start()
    return run, thread


def run_sync(
    action: Action,
    config: Config,
    engine: Engine,
    limits: Limits,
    origin: str,
    claude: list[str] | None = None,
    plugin_dir: Path | None = None,
) -> ClaudeRun:
    """Run an action without offer and wait for its end: what a scheduled task needs."""
    run, thread = start(action, None, config, engine, limits, origin, claude, plugin_dir)
    if thread is not None:
        thread.join()
    with session(engine) as db:
        finished = db.get(ClaudeRun, run.id)
    assert finished is not None
    return finished


def stop(run_id: int) -> bool:
    """Stop the run if it is the one in progress; False when it was not running."""
    with _runs.lock:
        if _runs.run_id != run_id or _runs.process is None:
            return False
        _runs.stopped = True
        process = _runs.process
    _kill(process)
    return True


def mark_interrupted(engine: Engine) -> int:
    """Close the runs a crash or a closed window left `running`. A scheduled task runs in its own
    process and may still be going: only its runs older than the timeout are closed."""
    stale = now() - timedelta(seconds=RUN_TIMEOUT_S)
    with session(engine) as db:
        runs = db.exec(
            select(ClaudeRun).where(
                ClaudeRun.status == RunStatus.RUNNING,
                or_(ClaudeRun.origin == "ui", col(ClaudeRun.started_at) < stale),
            )
        ).all()
        for run in runs:
            run.status = RunStatus.INTERRUPTED
            run.finished_at = now()
            db.add(run)
        db.commit()
    return len(runs)


def final_text(engine: Engine, run_id: int) -> str:
    """The run's last word: Claude's final answer, or why it stopped."""
    with session(engine) as db:
        text = db.exec(
            select(ClaudeEvent.text)
            .where(ClaudeEvent.run_id == run_id, col(ClaudeEvent.kind).in_(["result", "error"]))
            .order_by(col(ClaudeEvent.seq).desc())
        ).first()
    return text or ""
