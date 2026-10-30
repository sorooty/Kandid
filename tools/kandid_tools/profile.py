"""Schema of `profile.yaml`: the only source of facts for every generated document."""

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from kandid_tools.files import load_yaml


class Lang(StrEnum):
    FR = "fr"
    EN = "en"


# A text is either the same in every language or given per language.
Localized = str | dict[Lang, str]

Id = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")]

DEFAULT_WORDING = "default"


class MissingTranslationError(ValueError):
    pass


def localize(value: Localized, lang: Lang) -> str:
    if isinstance(value, str):
        return value
    if lang not in value:
        raise MissingTranslationError(f"texte manquant en '{lang}' : {value}")
    return value[lang]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Link(Strict):
    label: str
    url: str


class Identity(Strict):
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    city: str
    # Display order is the list order: the user puts the link they prefer first.
    links: list[Link] = []


class Header(Strict):
    title: Localized | None = None
    subtitle: Localized | None = None


class Education(Strict):
    school: str
    location: str | None = None
    dates: Localized
    lines: list[Localized] = []


def _check_wordings(wordings: dict[str, Any], owner: str) -> None:
    if DEFAULT_WORDING not in wordings:
        raise ValueError(f"{owner} : la formulation '{DEFAULT_WORDING}' est obligatoire")


class Experience(Strict):
    """Alternative wordings rephrase the same facts; they never add one."""

    id: Id
    role: Localized
    company: str
    dates: Localized
    wordings: dict[str, list[Localized]]

    @model_validator(mode="after")
    def _has_default(self) -> "Experience":
        _check_wordings(self.wordings, f"expérience '{self.id}'")
        return self


class ProjectStatus(StrEnum):
    DONE = "done"
    IN_PROGRESS = "in_progress"


class Project(Strict):
    id: Id
    title: Localized
    tech: list[str] = []
    dates: Localized
    status: ProjectStatus = ProjectStatus.DONE
    wordings: dict[str, Localized]

    @model_validator(mode="after")
    def _has_default(self) -> "Project":
        _check_wordings(self.wordings, f"projet '{self.id}'")
        return self


class SkillGroup(Strict):
    id: Id
    label: Localized
    items: list[str]


class CertificationStatus(StrEnum):
    OBTAINED = "obtained"
    IN_PROGRESS = "in_progress"


class Certification(Strict):
    name: str
    status: CertificationStatus = CertificationStatus.OBTAINED


class Language(Strict):
    name: Localized
    level: Localized


# An empty term would match every document.
Term = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Rules(Strict):
    forbidden_terms: list[Term] = []
    # Tools the user has not practiced: never in a CV, stated frankly in a letter.
    unconfirmed_skills: list[Term] = []
    default_project: Id | None = None
    project_count: int = Field(default=4, ge=1)
    # Free instructions for the letter skill (e.g. argue for the wanted duration).
    letter: list[str] = []


class Profile(Strict):
    identity: Identity
    header: Header = Header()
    summary: Localized | None = None
    education: list[Education] = []
    experiences: list[Experience] = []
    projects: list[Project] = []
    skills: list[SkillGroup] = []
    certifications: list[Certification] = []
    languages: list[Language] = []
    soft_skills: list[Localized] = []
    associations: list[Localized] = []
    hobbies: list[Localized] = []
    rules: Rules = Rules()

    @model_validator(mode="after")
    def _unique_ids(self) -> "Profile":
        for kind, items in (
            ("expérience", self.experiences),
            ("projet", self.projects),
            ("groupe de compétences", self.skills),
        ):
            ids = [item.id for item in items]
            duplicates = sorted({i for i in ids if ids.count(i) > 1})
            if duplicates:
                raise ValueError(f"{kind} en double : {', '.join(duplicates)}")
        default = self.rules.default_project
        if default is not None and default not in {p.id for p in self.projects}:
            raise ValueError(f"rules.default_project '{default}' ne correspond à aucun projet")
        return self

    def experience(self, item_id: str) -> Experience | None:
        return next((e for e in self.experiences if e.id == item_id), None)

    def project(self, item_id: str) -> Project | None:
        return next((p for p in self.projects if p.id == item_id), None)

    def skill_group(self, item_id: str) -> SkillGroup | None:
        return next((g for g in self.skills if g.id == item_id), None)

    def fact_texts(self) -> list[str]:
        """Every text the profile states as a fact (rules excluded), in any language."""
        texts: list[str] = []
        stack: list[Any] = [self.model_dump(mode="json", exclude={"rules"})]
        while stack:
            value = stack.pop()
            if isinstance(value, str):
                texts.append(value)
            elif isinstance(value, dict):
                stack.extend(value.values())
            elif isinstance(value, list):
                stack.extend(value)
        return texts


def load_profile(path: Path) -> Profile:
    return Profile.model_validate(load_yaml(path))
