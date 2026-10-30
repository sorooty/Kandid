import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from kandid_tools.cli import app
from kandid_tools.config import Config, load_config
from kandid_tools.workspace import FileState, WorkspaceFile, permission_path, write

from conftest import CAMILLE


def config_for(data: Path, **paths) -> Config:
    return Config.model_validate(
        {
            "paths": {"data": str(data), **{k: str(v) for k, v in paths.items()}},
            "watch": {"contracts": ["alternance"], "keywords": ["data analyst"]},
            "tasks": {"digest": {"enabled": False, "at": "19:00"}},
        }
    )


def states(changes) -> dict:
    return {c.file: (c.state, c.written) for c in changes}


def test_permission_path_uses_the_posix_form():
    assert permission_path(Path(r"C:\Users\Camille\Mon CV")) == "//c/Users/Camille/Mon CV"


def test_first_write_creates_everything_but_settings(tmp_path):
    data, master = tmp_path / "kandid", tmp_path / "CV"
    (data).mkdir()
    (data / "profile.yaml").write_bytes((CAMILLE / "profile.yaml").read_bytes())
    config = config_for(data, master=master)
    changes = write(config, "kandid taches lancer", overwrite=set(), with_settings=False)
    assert states(changes) == {
        WorkspaceFile.CONFIG: (FileState.NEW, True),
        WorkspaceFile.CLAUDE: (FileState.NEW, True),
        WorkspaceFile.GUIDE: (FileState.NEW, True),
        WorkspaceFile.SETTINGS: (FileState.NEW, False),
    }
    assert load_config(data / "config.yaml") == config
    claude = (data / "CLAUDE.md").read_text(encoding="utf-8")
    assert "recherche d'alternance" in claude
    assert "Camille" in claude and str(master) in claude
    guide = (data / "A_SAVOIR.md").read_text(encoding="utf-8")
    assert "| veille | 08:30 |" in guide
    assert "| digest |" not in guide
    assert "0.50 $" in guide


def test_existing_files_are_only_replaced_when_asked(tmp_path):
    data = tmp_path / "kandid"
    config = config_for(data)
    write(config, "k", overwrite=set(), with_settings=True)
    assert states(write(config, "k", overwrite=set(), with_settings=True))[
        WorkspaceFile.CONFIG
    ] == (FileState.SAME, False)

    changed = config.model_copy(
        update={"watch": config.watch.model_copy(update={"keywords": ["bi"]})}
    )
    kept = write(changed, "k", overwrite=set(), with_settings=True)
    config_change = next(c for c in kept if c.file is WorkspaceFile.CONFIG)
    assert (config_change.state, config_change.written) == (FileState.CHANGED, False)
    assert "+  - bi" in config_change.diff
    replaced = write(changed, "k", overwrite={WorkspaceFile.CONFIG}, with_settings=True)
    assert states(replaced)[WorkspaceFile.CONFIG] == (FileState.CHANGED, True)
    assert load_config(data / "config.yaml").watch.keywords == ["bi"]


def test_settings_protect_master_and_point_kandid_to_the_data(tmp_path):
    data, master = tmp_path / "kandid", tmp_path / "CV"
    write(config_for(data, master=master), "k", overwrite=set(), with_settings=True)
    settings = json.loads((data / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert f"Edit({permission_path(master)}/**)" in settings["permissions"]["deny"]
    assert settings["permissions"]["allow"] == ["Bash(kandid *)"]
    # The conftest sets KANDID_HOME elsewhere: this data folder is not the default one.
    assert settings["env"] == {"KANDID_HOME": str(data)}


def test_cli_write_reports_and_respects_the_settings_flag(tmp_path):
    data = tmp_path / "kandid"
    draft = tmp_path / "brouillon.yaml"
    draft.write_text(yaml.safe_dump({"paths": {"data": str(data)}}), encoding="utf-8")
    result = CliRunner().invoke(app, ["setup", "ecrire", str(draft), "--json"])
    assert result.exit_code == 0, result.output
    rows = {row["file"]: row for row in json.loads(result.stdout)}
    assert rows[".claude/settings.json"]["written"] is False
    assert rows["config.yaml"]["written"] is True
    assert not (data / ".claude").exists()
