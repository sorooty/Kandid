"""`kandid importer`, `kandid setup` and `kandid taches`, called by `/kandid:setup` and the
scheduler."""

import json
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from kandid_tools.bridge import RunStatus
from kandid_tools.cli_common import ConfigOpt, JsonOpt, fail, new_app, user_errors
from kandid_tools.config import Config, TaskName, user_config
from kandid_tools.db import open_db
from kandid_tools.files import load_yaml
from kandid_tools.importer import import_cv
from kandid_tools.scheduler import (
    SchedulerError,
    install,
    listed,
    plugin_root,
    remove,
    run_task,
    task_command,
)
from kandid_tools.workspace import FileState, WorkspaceFile, write

setup_app = new_app("Écrit les fichiers de l'espace Kandid à partir des réponses de /kandid:setup.")
tasks_app = new_app("Tâches planifiées : elles préparent, elles n'envoient jamais rien.")


def importer(
    path: Annotated[
        Path, typer.Argument(exists=True, dir_okay=False, help="CV .tex, .pdf ou .docx")
    ],
) -> None:
    """Texte d'un CV existant, découpé en sections (JSON). Le fichier n'est jamais modifié."""
    with user_errors():
        imported = import_cv(path)
    typer.echo(imported.model_dump_json(indent=2))


def _scheduler_command() -> str:
    try:
        return subprocess.list2cmdline(task_command(plugin_root()))
    except SchedulerError:
        return "kandid taches lancer"


@setup_app.command("ecrire")
def write_command(
    draft: Annotated[
        Path, typer.Argument(exists=True, dir_okay=False, help="config.yaml proposé (brouillon)")
    ],
    overwrite: Annotated[
        list[WorkspaceFile] | None,
        typer.Option("--ecraser", help="Fichier existant à remplacer (répétable)"),
    ] = None,
    with_settings: Annotated[
        bool, typer.Option("--settings", help="Écrit aussi .claude/settings.json (accord donné)")
    ] = False,
    as_json: JsonOpt = False,
) -> None:
    """Écrit config.yaml, CLAUDE.md, A_SAVOIR.md et, sur accord, les permissions Claude Code."""
    with user_errors():
        config = Config.model_validate(load_yaml(draft) or {})
        changes = write(
            config,
            _scheduler_command(),
            overwrite=set(overwrite or []),
            with_settings=with_settings,
        )
    if as_json:
        typer.echo(json.dumps([c.model_dump(mode="json") for c in changes], ensure_ascii=False))
        return
    for change in changes:
        done = "écrit" if change.written else "non écrit"
        typer.echo(f"{change.file.value} : {change.state.value}, {done}")
        if change.state is FileState.CHANGED and not change.written:
            typer.echo(change.diff)


TaskArg = Annotated[TaskName, typer.Argument(help="veille, relances ou digest")]


def _scheduler_errors(action):
    try:
        return action()
    except SchedulerError as error:
        fail(str(error))


@tasks_app.command("installer")
def install_command(config_path: ConfigOpt = None) -> None:
    """Programme les tâches activées dans config.yaml et retire les autres."""
    with user_errors():
        config = user_config(config_path)
    installed = _scheduler_errors(lambda: install(config))
    for task in installed:
        typer.echo(f"{task.value} : tous les jours à {config.tasks.settings(task).at}")
    if not installed:
        typer.echo("aucune tâche activée")


@tasks_app.command("lister")
def list_command(as_json: JsonOpt = False) -> None:
    """Tâches Kandid du Planificateur, avec leur prochain lancement."""
    tasks = _scheduler_errors(listed)
    if as_json:
        typer.echo(json.dumps([t.model_dump() for t in tasks], ensure_ascii=False))
        return
    for task in tasks:
        typer.echo(f"{task.name} : {task.state}, prochain lancement {task.next or 'aucun'}")
    if not tasks:
        typer.echo("aucune tâche Kandid programmée")


@tasks_app.command("supprimer")
def remove_command() -> None:
    """Retire toutes les tâches Kandid du Planificateur."""
    _scheduler_errors(remove)
    typer.echo("tâches Kandid supprimées")


@tasks_app.command("lancer")
def run_command(
    task: TaskArg,
    config_path: ConfigOpt = None,
    plugin_dir: Annotated[
        Path | None,
        typer.Option(
            "--plugin-dir", file_okay=False, help="Copie locale du plugin (développement)"
        ),
    ] = None,
) -> None:
    """Lance une tâche maintenant (c'est ce que le Planificateur appelle)."""
    with user_errors():
        config = user_config(config_path)
        run = run_task(task, config, open_db(config.paths.data), plugin_dir=plugin_dir)
    ok = run.status == RunStatus.OK
    cost = f"{run.cost_usd:.2f} $" if run.cost_usd is not None else "coût inconnu"
    typer.echo(f"{task.value} : {'terminée' if ok else 'échec'}, {cost}, rapport {run.report}")
    if not ok:
        raise typer.Exit(1)
