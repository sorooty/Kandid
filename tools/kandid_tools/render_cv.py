"""CV `.tex` from a profile and a per-offer spec."""

from kandid_tools.latex import environment
from kandid_tools.profile import (
    CertificationStatus,
    Lang,
    Localized,
    Profile,
    ProjectStatus,
    localize,
)
from kandid_tools.spec import Pick, Spec, spec_errors

# Section titles of the template. wrapcheck reads them back from the PDF.
LABELS: dict[Lang, dict[str, str]] = {
    Lang.FR: {
        "babel": "french",
        "experience": "Expériences professionnelles",
        "projects": "Projets",
        "education": "Formation",
        "skills": "Compétences",
        "languages": "Langues",
        "certifications": "Certifications",
        "obtained": "Obtenues",
        "certifications_in_progress": "En cours",
        "qualities": "Savoir-être",
        "soft_skills": "Soft skills",
        "associations": "Associations",
        "hobbies": "Centres d'intérêt",
        "in_progress": "en cours",
        "colon": " :",
    },
    Lang.EN: {
        "babel": "english",
        "experience": "Professional Experience",
        "projects": "Projects",
        "education": "Education",
        "skills": "Skills",
        "languages": "Languages",
        "certifications": "Certifications",
        "obtained": "Obtained",
        "certifications_in_progress": "In progress",
        "qualities": "Personal Qualities",
        "soft_skills": "Soft skills",
        "associations": "Volunteering",
        "hobbies": "Interests",
        "in_progress": "in progress",
        "colon": ":",
    },
}


class SpecError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("spec invalide :\n" + "\n".join(f"- {e}" for e in errors))
        self.errors = errors


def chosen_projects(profile: Profile, spec: Spec) -> list[Pick]:
    """The spec's projects, with the default project first when too few were chosen."""
    picks = list(spec.projects)
    default = profile.rules.default_project
    if (
        default is not None
        and len(picks) < profile.rules.project_count
        and default not in {p.id for p in picks}
    ):
        picks.insert(0, Pick(id=default))
    return picks


def build_context(profile: Profile, spec: Spec) -> dict[str, object]:
    errors = spec_errors(spec, profile)
    if errors:
        raise SpecError(errors)
    lang = spec.lang
    labels = LABELS[lang]

    def tr(value: Localized | None) -> str | None:
        return None if value is None else localize(value, lang)

    def joined(values: list[Localized]) -> str:
        return ", ".join(tr(v) or "" for v in values)

    # Ids were checked by spec_errors, so plain lookups cannot fail.
    experience_by_id = {e.id: e for e in profile.experiences}
    project_by_id = {p.id: p for p in profile.projects}
    group_by_id = {g.id: g for g in profile.skills}

    experiences = []
    for pick in spec.experiences:
        experience = experience_by_id[pick.id]
        experiences.append(
            {
                "role": tr(experience.role),
                "company": experience.company,
                "dates": tr(experience.dates),
                "bullets": [tr(b) for b in experience.wordings[pick.wording]],
            }
        )

    projects = []
    for pick in chosen_projects(profile, spec):
        project = project_by_id[pick.id]
        projects.append(
            {
                "title": tr(project.title),
                "tech": ", ".join(project.tech),
                "dates": tr(project.dates),
                "in_progress": project.status is ProjectStatus.IN_PROGRESS,
                "text": tr(project.wordings[pick.wording]),
            }
        )

    groups = [group_by_id[i] for i in spec.skills] if spec.skills else profile.skills
    skills = [(tr(g.label), ", ".join(g.items)) for g in groups]
    languages = " ; ".join(f"{tr(x.name)} {tr(x.level)}" for x in profile.languages)
    skills.append((labels["languages"], languages))

    def certifications(status: CertificationStatus) -> str:
        return " | ".join(c.name for c in profile.certifications if c.status is status)

    label_sections = [
        (labels["skills"], skills),
        (
            labels["certifications"],
            [
                (labels["obtained"], certifications(CertificationStatus.OBTAINED)),
                (
                    labels["certifications_in_progress"],
                    certifications(CertificationStatus.IN_PROGRESS),
                ),
            ],
        ),
        (
            labels["qualities"],
            [
                (labels["soft_skills"], joined(profile.soft_skills)),
                (labels["associations"], joined(profile.associations)),
                (labels["hobbies"], joined(profile.hobbies)),
            ],
        ),
    ]
    # Empty rows and sections are dropped so the template never prints a bare label.
    label_sections = [
        (title, kept)
        for title, rows in label_sections
        if (kept := [(label, text) for label, text in rows if text])
    ]

    return {
        "labels": labels,
        "identity": profile.identity,
        "title": spec.title or tr(profile.header.title),
        "subtitle": spec.subtitle or tr(profile.header.subtitle),
        "summary": spec.summary or tr(profile.summary),
        "experiences": experiences,
        "projects": projects,
        "projects_title": spec.projects_title or labels["projects"],
        "education": [
            {
                "school": e.school,
                "location": e.location,
                "dates": tr(e.dates),
                "lines": [tr(line) for line in e.lines],
            }
            for e in profile.education
        ],
        "label_sections": label_sections,
    }


def render_cv(profile: Profile, spec: Spec) -> str:
    return environment().get_template("cv.tex.j2").render(build_context(profile, spec))
