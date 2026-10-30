"""User settings from `config.yaml`. Defaults reproduce the usual French folder conventions."""

from pathlib import Path

from kandid_tools.files import load_yaml
from kandid_tools.profile import Strict


class NamingConfig(Strict):
    pattern: str = "{doc}_{first}_{last}_{company}_{contract}_{role}_{lang}_{month}"
    contracts: list[str] = ["Alternance", "Stage", "Stage-PFE", "CDI", "Freelance"]
    contract_folders: dict[str, str] = {
        "Alternance": "ALTERNANCE",
        "Stage": "STAGE",
        "Stage-PFE": "STAGE",
    }
    other_folder: str = "AUTRES"
    # Folder of each document type, relative to the applications folder. Offer and ATS
    # reports have no entry: they are filed next to the CV.
    layout: dict[str, str] = {
        "CV": "CV/{folder}",
        "LM": "LETTRES_MOTIVATION/{folder}",
    }


class Config(Strict):
    naming: NamingConfig = NamingConfig()


def load_config(path: Path | None) -> Config:
    if path is None:
        return Config()
    return Config.model_validate(load_yaml(path) or {})
