"""Files `/setup` writes in the data folder: settings, the workspace CLAUDE.md, A_SAVOIR.md and the
proposed Claude Code permissions. Nothing existing is replaced unless the user said so for that
file."""

import difflib
import json
from enum import StrEnum
from pathlib import Path, PureWindowsPath

import yaml
from jinja2 import Environment, PackageLoader, StrictUndefined
from pydantic import BaseModel

from kandid_tools.config import CONFIG_NAME, PROFILE_NAME, Config, TaskName, default_data_dir
from kandid_tools.files import read_text
from kandid_tools.profile import load_profile


class WorkspaceFile(StrEnum):
    CONFIG = CONFIG_NAME
    CLAUDE = "CLAUDE.md"
    GUIDE = "A_SAVOIR.md"
    SETTINGS = ".claude/settings.json"


class FileState(StrEnum):
    NEW = "nouveau"
    SAME = "identique"
    CHANGED = "différent"


class FileChange(BaseModel):
    file: WorkspaceFile
    path: Path
    state: FileState
    written: bool = False
    diff: str = ""


TASK_ROLES = {
    TaskName.WATCH: "cherche les nouvelles offres et les note",
    TaskName.FOLLOW_UPS: "liste les relances dues et prépare les brouillons",
    TaskName.DIGEST: "résume la journée et les actions du lendemain",
}
_CONTRACT_WORDS = {
    "alternance": "d'alternance",
    "stage": "de stage",
    "cdi": "de CDI",
    "cdd": "de CDD",
    "interim": "d'intérim",
    "freelance": "de missions freelance",
}
# Destructive commands Claude never needs in this folder.
_DENY = [
    "Bash(rm -rf *)",
    "Bash(rm -r *)",
    "Bash(git push --force *)",
    "Bash(git push -f *)",
    "Bash(git reset --hard *)",
    "Bash(git clean -f*)",
    "Read(./.env)",
    "Read(./.env.*)",
]


def permission_path(path: Path) -> str:
    """A path in permission rule syntax: `//c/Users/...`, the POSIX form matched on Windows."""
    windows = PureWindowsPath(path)
    if windows.drive.endswith(":"):
        return "//" + windows.drive[0].lower() + "/" + "/".join(windows.parts[1:])
    return "/" + path.as_posix()


def settings(config: Config) -> dict:
    deny = list(_DENY)
    if config.paths.master is not None:
        # Edit rules also cover Write and shell redirections: a second layer if a hook cannot start.
        deny.append(f"Edit({permission_path(config.paths.master)}/**)")
    result: dict = {"permissions": {"allow": ["Bash(kandid *)"], "deny": deny}}
    if config.paths.data != default_data_dir():
        # `kandid` looks for its data in ~/.kandid unless told otherwise.
        result["env"] = {"KANDID_HOME": str(config.paths.data)}
    return result


def _search(config: Config) -> str:
    words = [_CONTRACT_WORDS[c.value] for c in config.watch.contracts]
    return " et ".join(words) if words else "d'emploi"


def _environment() -> Environment:
    return Environment(
        loader=PackageLoader("kandid_tools", "templates/workspace"),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
        autoescape=False,
    )


def contents(config: Config, task_command: str) -> dict[WorkspaceFile, str]:
    data = config.paths.data
    profile_path = data / PROFILE_NAME
    first_name = (
        load_profile(profile_path).identity.first_name if profile_path.is_file() else "the user"
    )
    tasks = [
        {"name": task.value, "at": config.tasks.settings(task).at, "role": TASK_ROLES[task]}
        for task in TaskName
        if config.tasks.settings(task).enabled
    ]
    values = {
        "search": _search(config),
        "first_name": first_name,
        "profile": profile_path,
        "data": data,
        "applications": config.paths.applications_dir,
        "master": config.paths.master,
        "naming_pattern": config.naming.pattern,
        "tasks": tasks,
        "max_turns": config.tasks.max_turns,
        "max_budget_usd": config.tasks.max_budget_usd,
        "ui_max_turns": config.ui.max_turns,
        "ui_max_budget_usd": config.ui.max_budget_usd,
        "task_command": task_command,
    }
    env = _environment()
    dumped = config.model_dump(mode="json", exclude_defaults=True)
    dumped.setdefault("paths", {})["data"] = str(data)
    return {
        WorkspaceFile.CONFIG: yaml.safe_dump(dumped, allow_unicode=True, sort_keys=False),
        WorkspaceFile.CLAUDE: env.get_template("CLAUDE.md.j2").render(values),
        WorkspaceFile.GUIDE: env.get_template("A_SAVOIR.md.j2").render(values),
        WorkspaceFile.SETTINGS: json.dumps(settings(config), indent=2, ensure_ascii=False) + "\n",
    }


def write(
    config: Config, task_command: str, *, overwrite: set[WorkspaceFile], with_settings: bool
) -> list[FileChange]:
    """Write new files, and changed ones only when named in `overwrite`. Settings are only written
    when the user accepted them (`with_settings`)."""
    changes = []
    for file, text in contents(config, task_command).items():
        path = config.paths.data / file.value
        old = read_text(path) if path.is_file() else None
        if old is None:
            state = FileState.NEW
        else:
            state = FileState.SAME if old == text else FileState.CHANGED
        change = FileChange(file=file, path=path, state=state)
        if state is FileState.CHANGED:
            change.diff = "".join(
                difflib.unified_diff(
                    old.splitlines(keepends=True),
                    text.splitlines(keepends=True),
                    "actuel",
                    "proposé",
                )
            )
        allowed = file is not WorkspaceFile.SETTINGS or with_settings
        if allowed and (
            state is FileState.NEW or (state is FileState.CHANGED and file in overwrite)
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
            change.written = True
        changes.append(change)
    return changes
