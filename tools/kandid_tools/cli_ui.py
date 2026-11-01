"""`kandid ui`: the local CRM in the browser."""

import subprocess
import threading
import time
import webbrowser
from pathlib import Path
from typing import Annotated

import typer

from kandid_tools.cli_common import ConfigOpt, fail, user_errors
from kandid_tools.config import user_config
from kandid_tools.scheduler import SchedulerError, plugin_root, task_command

SHORTCUT = "Ouvrir Kandid.bat"


def _open_when_ready(server: object, url: str) -> None:
    while not getattr(server, "started", False):
        time.sleep(0.1)
    webbrowser.open(url)


def ui(
    port: Annotated[
        int | None, typer.Option(help="Port local (sinon celui de config.yaml)")
    ] = None,
    no_browser: Annotated[
        bool, typer.Option("--no-browser", help="N'ouvre pas le navigateur")
    ] = False,
    shortcut: Annotated[
        bool,
        typer.Option("--raccourci", help=f"Écrit « {SHORTCUT} » dans le dossier de données"),
    ] = False,
    config_path: ConfigOpt = None,
    plugin_dir: Annotated[
        Path | None,
        typer.Option(
            "--plugin-dir", file_okay=False, help="Copie locale du plugin (développement)"
        ),
    ] = None,
) -> None:
    """Ouvre le CRM Kandid dans le navigateur (serveur local, arrêt avec Ctrl+C)."""
    with user_errors():
        config = user_config(config_path)
    if shortcut:
        try:
            # Same uv command as the scheduled tasks, minus `taches lancer`.
            command = [*task_command(plugin_root())[:-2], "ui"]
        except SchedulerError as error:
            fail(str(error))
        path = config.paths.data / SHORTCUT
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"@echo off\r\n{subprocess.list2cmdline(command)}\r\n", encoding="utf-8")
        typer.echo(f"raccourci écrit : {path}")
        return
    # Imported here: every other `kandid` command, hooks included, starts without the web stack.
    import uvicorn

    from kandid_api.app import create_app

    port = port or config.ui.port
    url = f"http://127.0.0.1:{port}/"
    app = create_app(config, plugin_dir=plugin_dir)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    if not no_browser:
        threading.Thread(target=_open_when_ready, args=(server, url), daemon=True).start()
    typer.echo(f"Kandid : {url} (Ctrl+C pour arrêter)")
    server.run()
