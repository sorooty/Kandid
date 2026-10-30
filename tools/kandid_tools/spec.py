"""Schema of the per-offer `spec.yaml`: which profile facts go in the CV, and their wording."""

from pathlib import Path

from pydantic import Field, field_validator

from kandid_tools.files import load_yaml
from kandid_tools.profile import DEFAULT_WORDING, Id, Lang, Profile, Strict


class Pick(Strict):
    id: Id
    wording: str = DEFAULT_WORDING


def _to_pick(value: object) -> object:
    return {"id": value} if isinstance(value, str) else value


class Offer(Strict):
    company: str
    role: str
    url: str | None = None


class Spec(Strict):
    offer: Offer
    contract: str
    lang: Lang = Lang.FR
    title: str | None = None
    subtitle: str | None = None
    summary: str | None = None
    experiences: list[Pick] = Field(min_length=1)
    projects: list[Pick] = []
    projects_title: str | None = None
    # Skill group ids, in display order; empty means every group of the profile.
    skills: list[Id] = []

    @field_validator("experiences", "projects", mode="before")
    @classmethod
    def _accept_bare_ids(cls, value: object) -> object:
        return [_to_pick(v) for v in value] if isinstance(value, list) else value


def spec_errors(spec: Spec, profile: Profile) -> list[str]:
    """Everything in the spec that the profile does not back."""
    errors: list[str] = []
    for pick in spec.experiences:
        experience = profile.experience(pick.id)
        if experience is None:
            errors.append(f"expérience inconnue : '{pick.id}'")
        elif pick.wording not in experience.wordings:
            errors.append(f"formulation inconnue pour l'expérience '{pick.id}' : '{pick.wording}'")
    for pick in spec.projects:
        project = profile.project(pick.id)
        if project is None:
            errors.append(f"projet inconnu : '{pick.id}'")
        elif pick.wording not in project.wordings:
            errors.append(f"formulation inconnue pour le projet '{pick.id}' : '{pick.wording}'")
    errors.extend(
        f"groupe de compétences inconnu : '{group_id}'"
        for group_id in spec.skills
        if profile.skill_group(group_id) is None
    )
    return errors


def load_spec(path: Path) -> Spec:
    return Spec.model_validate(load_yaml(path))
