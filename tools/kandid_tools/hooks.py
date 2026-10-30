"""Claude Code hooks of the plugin. Each reads the hook's JSON payload and returns the JSON answer.

They enforce the guardrails whatever the prompt says: the master CV folder is read-only, nothing
is sent without the user's yes, and a generated document claiming an unknown skill is sent back.
Once Python runs, a hook that cannot decide asks the user rather than letting the call through.
A hook that cannot start at all (uv missing, timeout) lets it through: Claude Code treats that as
a non-blocking error, so the CLI and the permission rules written by `/setup` repeat the checks.
"""

import json
import re
import sys
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Any

from kandid_tools import honesty
from kandid_tools.config import PROFILE_NAME, Config, user_config
from kandid_tools.files import is_inside, read_text
from kandid_tools.profile import load_profile

_WRITE_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"})
_SHELL_TOOLS = frozenset({"Bash", "PowerShell"})
# Actions that reach someone else: a message, an invitation, a shared or published document.
_SEND = re.compile(
    r"send|reply|forward|submit|share|post|publish|invite|respond|comment|upload"
    r"|(create|update)_?event",
    re.IGNORECASE,
)


class Hook(StrEnum):
    PROTECT_MASTER = "protect-master"
    CONFIRM_SEND = "confirm-send"
    CHECK_DOCUMENT = "check-document"


Payload = dict[str, Any]
Answer = dict[str, Any] | None


def _pre_tool(decision: str, reason: str) -> Answer:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }


def _context(text: str) -> Answer:
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}}


def _target(payload: Payload) -> Path | None:
    tool_input = payload.get("tool_input") or {}
    raw = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(raw, str) or not raw:
        return None
    path = Path(raw)
    return path if path.is_absolute() else Path(payload.get("cwd") or ".") / path


def _slashes(text: str) -> str:
    return text.replace("\\", "/").casefold()


def _spellings(folder: Path) -> set[str]:
    """How a shell command may write the folder: native, Git Bash (`/c/...`) or from home."""
    native = _slashes(str(folder)).rstrip("/")
    forms = {native}
    if len(native) > 2 and native[1] == ":":
        forms.add(f"/{native[0]}{native[2:]}")
    home = _slashes(str(Path.home())).rstrip("/")
    if native.startswith(home + "/"):
        rest = native[len(home) :]
        for prefix in ("~", "$home", "${home}", "%userprofile%", "$env:userprofile"):
            forms.add(prefix + rest)
    return forms


def protect_master(payload: Payload, config: Config) -> Answer:
    master = config.paths.master
    if master is None:
        return None
    tool = payload.get("tool_name", "")
    if tool in _WRITE_TOOLS:
        target = _target(payload)
        if target is not None and is_inside(target, master):
            return _pre_tool(
                "deny", f"Le dossier maître ({master}) est en lecture seule pour Kandid."
            )
    if tool in _SHELL_TOOLS:
        command = _slashes(str((payload.get("tool_input") or {}).get("command", "")))
        cwd = payload.get("cwd")
        # A command can write anywhere: naming the master folder, or running inside it, is enough
        # to ask first. Best effort (a relative path from its parent gets through): the CLI and
        # the permission rules written by `/setup` are the other layers.
        if any(form in command for form in _spellings(master)) or (
            isinstance(cwd, str) and cwd and is_inside(Path(cwd), master)
        ):
            return _pre_tool("ask", f"Cette commande touche le dossier maître ({master}).")
    return None


def confirm_send(payload: Payload, _config: Config) -> Answer:
    tool = str(payload.get("tool_name", ""))
    action = tool.rsplit("__", 1)[-1]
    if tool.startswith("mcp__") and _SEND.search(action):
        return _pre_tool("ask", "Kandid n'envoie rien sans ton accord : vérifie avant de valider.")
    return None


def check_document(payload: Payload, config: Config) -> Answer:
    target = _target(payload)
    if (
        payload.get("tool_name") not in _WRITE_TOOLS
        or target is None
        or target.suffix.lower() != ".tex"
        or not is_inside(target, config.paths.applications_dir)
    ):
        return None
    profile_path = config.paths.data / PROFILE_NAME
    if not profile_path.is_file():
        return _context(f"Contrôle d'honnêteté impossible : {profile_path} introuvable.")
    # Generated names start with the document type ("LM_..." for a letter).
    letter = target.name.upper().startswith("LM")
    text = honesty.untex(read_text(target))
    report = honesty.check_text(text, load_profile(profile_path), letter=letter)
    if not report.ok:
        return {"decision": "block", "reason": honesty.to_text(report)}
    return _context(honesty.to_text(report)) if report.issues else None


_HOOKS: dict[Hook, Callable[[Payload, Config], Answer]] = {
    Hook.PROTECT_MASTER: protect_master,
    Hook.CONFIRM_SEND: confirm_send,
    Hook.CHECK_DOCUMENT: check_document,
}


def run(hook: Hook, raw: bytes | str) -> str:
    """The hook's stdout: JSON, or nothing when the hook has no opinion."""
    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        answer = _HOOKS[hook](json.loads(text), user_config())
    except Exception as error:
        # Only the error type: its message could quote the profile or a document.
        reason = f"Kandid n'a pas pu vérifier cette action ({type(error).__name__})."
        if hook is Hook.CHECK_DOCUMENT:
            answer = _context(reason)
        else:
            answer = _pre_tool("ask", reason + " Confirme toi-même.")
    return json.dumps(answer, ensure_ascii=False) if answer else ""


def main() -> None:
    """`python -m kandid_tools.hooks <name>`: lighter than the CLI, which loads every command."""
    output = run(Hook(sys.argv[1]), sys.stdin.buffer.read())
    sys.stdout.buffer.write(output.encode("utf-8"))


if __name__ == "__main__":
    main()
