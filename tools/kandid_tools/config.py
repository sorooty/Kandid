"""User settings from `config.yaml`. Defaults reproduce the usual French folder conventions."""

import os
from enum import StrEnum
from pathlib import Path
from typing import Annotated

from pydantic import Field

from kandid_tools.files import load_yaml
from kandid_tools.profile import Strict, Term


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


class ContractKind(StrEnum):
    """Contract families every source is mapped to."""

    WORK_STUDY = "alternance"
    INTERNSHIP = "stage"
    PERMANENT = "cdi"
    FIXED_TERM = "cdd"
    TEMPORARY = "interim"
    FREELANCE = "freelance"


class Area(Strict):
    city: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_km: int = Field(default=30, ge=0, le=200)
    departements: list[Annotated[str, Field(pattern=r"^(\d{2,3}|2[AB])$")]] = []
    # Accept remote offers wherever the company is.
    remote: bool = False


class Ats(StrEnum):
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    SMARTRECRUITERS = "smartrecruiters"
    RECRUITEE = "recruitee"


class Company(Strict):
    name: str
    ats: Ats
    # Goes into a URL path or a subdomain, so only safe characters.
    board: Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")]


class SourceSettings(Strict):
    enabled: bool = True
    # Names of the environment variables holding this source's secrets, never the secrets. The
    # pattern stops a pasted secret, which would otherwise be echoed as a missing variable name.
    env: dict[str, Annotated[str, Field(pattern=r"^[A-Z_][A-Z0-9_]{0,63}$")]] = {}


class SourcesConfig(Strict):
    labonnealternance: SourceSettings = SourceSettings(env={"token": "KANDID_LBA_TOKEN"})
    francetravail: SourceSettings = SourceSettings(
        env={"client_id": "KANDID_FT_CLIENT_ID", "client_secret": "KANDID_FT_CLIENT_SECRET"}
    )
    adzuna: SourceSettings = SourceSettings(
        env={"app_id": "KANDID_ADZUNA_APP_ID", "app_key": "KANDID_ADZUNA_APP_KEY"}
    )
    careers: SourceSettings = SourceSettings()
    # LinkedIn's terms forbid automated access: the user turns it on knowingly (ADR 0013).
    linkedin_guest: SourceSettings = SourceSettings(enabled=False)


class WatchConfig(Strict):
    contracts: list[ContractKind] = []
    keywords: list[Term] = []
    # ROME job codes, used by La bonne alternance which does not search by keywords.
    romes: list[Annotated[str, Field(pattern=r"^[A-Z]\d{4}$")]] = []
    area: Area = Area()
    exclude: list[Term] = []
    min_score: int = Field(default=0, ge=0, le=100)
    max_age_days: int = Field(default=31, ge=1, le=365)
    country: Annotated[str, Field(pattern=r"^[a-z]{2}$")] = "fr"
    companies: list[Company] = []
    sources: SourcesConfig = SourcesConfig()


def default_data_dir() -> Path:
    """`KANDID_HOME` when set (tests, several profiles), else `~/.kandid`."""
    return Path(os.environ.get("KANDID_HOME") or Path.home() / ".kandid")


class Paths(Strict):
    data: Path = Field(default_factory=default_data_dir)


class Config(Strict):
    paths: Paths = Paths()
    naming: NamingConfig = NamingConfig()
    watch: WatchConfig = WatchConfig()


def load_config(path: Path | None) -> Config:
    if path is None:
        return Config()
    return Config.model_validate(load_yaml(path) or {})


def secrets_for(settings: SourceSettings) -> dict[str, str] | None:
    """The source's secrets from the environment, or None when one is missing."""
    values = {key: os.environ.get(variable, "") for key, variable in settings.env.items()}
    return values if all(values.values()) else None
