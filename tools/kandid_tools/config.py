"""User settings from `config.yaml`. Defaults reproduce the usual French folder conventions."""

import os
from enum import StrEnum
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator

from kandid_tools.files import load_yaml
from kandid_tools.profile import Strict, Term

CONFIG_NAME = "config.yaml"
PROFILE_NAME = "profile.yaml"
# Working files of an application (offer, sheet, spec, letter, reports): `<data>/offres/<id>`.
WORK_DIR = "offres"


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


class TaskName(StrEnum):
    WATCH = "veille"
    FOLLOW_UPS = "relances"
    DIGEST = "digest"


class TaskSettings(Strict):
    enabled: bool = True
    at: Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]


class TasksConfig(Strict):
    """Scheduled runs of `claude -p`. They prepare only; the caps bound what one run may cost."""

    veille: TaskSettings = TaskSettings(at="08:30")
    relances: TaskSettings = TaskSettings(at="09:00")
    digest: TaskSettings = TaskSettings(at="19:00")
    max_turns: int = Field(default=30, ge=1, le=200)
    max_budget_usd: float = Field(default=0.5, gt=0, le=10)

    def settings(self, task: TaskName) -> TaskSettings:
        return getattr(self, task.value)


class UiConfig(Strict):
    """The local CRM (`kandid ui`). Its runs prepare whole applications, hence higher caps than
    the scheduled tasks."""

    port: int = Field(default=8765, ge=1024, le=65535)
    max_turns: int = Field(default=80, ge=1, le=300)
    max_budget_usd: float = Field(default=3.0, gt=0, le=20)


def default_data_dir() -> Path:
    """`KANDID_HOME` when set (tests, several profiles), else `~/.kandid`."""
    return Path(os.environ.get("KANDID_HOME") or Path.home() / ".kandid")


class Paths(Strict):
    data: Path = Field(default_factory=default_data_dir)
    # Generated documents, one folder per application. Defaults to `<data>/applications`.
    applications: Path | None = None
    # The user's own CV folder: Kandid reads it and hooks refuse any write into it.
    master: Path | None = None

    @field_validator("data", "applications", "master", mode="after")
    @classmethod
    def _absolute(cls, value: Path | None) -> Path | None:
        # A "~" or relative path left as is would resolve against the session's folder, and the
        # master folder guard would silently never match.
        if value is None:
            return None
        expanded = Path(os.path.expandvars(os.path.expanduser(value)))
        if not expanded.is_absolute():
            raise ValueError(f"chemin absolu attendu : {value}")
        return expanded

    @property
    def applications_dir(self) -> Path:
        return self.applications or self.data / "applications"


_ATS_SENDERS = (
    "teamtailor-mail.com OR myworkday.com OR icims OR successfactors OR sapsf OR smartrecruiters"
    " OR welcometothejungle OR jobteaser OR apprentissage.beta.gouv.fr OR join.com OR lever.co"
    " OR greenhouse"
)


class MailQueries(Strict):
    """One search per connector, in its own syntax. `{days}` is replaced by `MailConfig.days`."""

    gmail: str = (
        "newer_than:{days}d -in:sent -category:promotions"
        " (subject:(candidature OR postulé OR application OR candidat OR applying)"
        f" OR from:({_ATS_SENDERS}))"
    )
    outlook: str = "candidature OR postulé OR postuler OR application OR candidate"


class MailConfig(Strict):
    """Reading recruiter answers. Patterns are lowercase substrings, matched without accents."""

    days: int = Field(default=60, ge=1, le=365)
    queries: MailQueries = MailQueries()
    # Job alerts and newsletters share the vocabulary of answers; they are dropped first.
    ignore_senders: list[Term] = [
        "jobalert", "match.indeed", "jobalerts-noreply", "newsletters-noreply", "newsletter",
        "marketing@", "news.", "seekube", "notifications-noreply@linkedin",
    ]  # fmt: skip
    ignore_subjects: list[Term] = [
        "offres d'emploi supplementaires", "jobs you may be interested", "job alert",
        "forum de recrutement", "salon",
    ]  # fmt: skip
    rejection: list[Term] = [
        "suite favorable", "pas ete retenue", "pas retenu", "autres profils", "autre candidat",
        "ne pas donner suite", "pas donner suite", "a ete pourvu", "deja pourvu", "unfortunately",
        "not been selected", "not to move forward", "regret",
    ]  # fmt: skip
    interview: list[Term] = [
        "entretien", "interview", "rendez-vous", "vos disponibilites", "echange telephonique",
        "call with",
    ]  # fmt: skip
    acknowledgement: list[Term] = [
        "bien recu", "bien ete envoyee", "accuse de reception", "candidature recue",
        "merci d'avoir postule", "merci pour votre candidature", "merci de votre candidature",
        "nous vous remercions", "thank you for applying", "we have received", "we received",
    ]  # fmt: skip


class Config(Strict):
    paths: Paths = Paths()
    naming: NamingConfig = NamingConfig()
    watch: WatchConfig = WatchConfig()
    tasks: TasksConfig = TasksConfig()
    ui: UiConfig = UiConfig()
    mail: MailConfig = MailConfig()


def load_config(path: Path | None) -> Config:
    if path is None:
        return Config()
    return Config.model_validate(load_yaml(path) or {})


def user_config(path: Path | None = None) -> Config:
    """The given file, else the data folder's `config.yaml` when it exists, else defaults."""
    default = default_data_dir() / CONFIG_NAME
    return load_config(path or (default if default.is_file() else None))


def secrets_for(settings: SourceSettings) -> dict[str, str] | None:
    """The source's secrets from the environment, or None when one is missing."""
    values = {key: os.environ.get(variable, "") for key, variable in settings.env.items()}
    return values if all(values.values()) else None
