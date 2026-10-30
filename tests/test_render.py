from datetime import date

import pytest

from kandid_tools.profile import Lang
from kandid_tools.render_cv import SpecError, chosen_projects, render_cv
from kandid_tools.render_lm import Letter, letter_date, render_lm
from kandid_tools.spec import Spec


def test_default_project_is_prepended_when_too_few(profile, datavia_spec):
    assert [p.id for p in chosen_projects(profile, datavia_spec)] == ["meteo", "rh", "avis", "rag"]


def test_default_project_not_added_twice(profile, datavia_spec):
    spec = Spec.model_validate({**datavia_spec.model_dump(), "projects": ["meteo", "rh"]})
    assert [p.id for p in chosen_projects(profile, spec)] == ["meteo", "rh"]


def test_cv_contains_chosen_wording_and_escapes_text(profile, datavia_spec):
    tex = render_cv(profile, datavia_spec)
    assert r"\textbf{1 200 sites clients}" in tex
    assert r"15 \% d'anomalies" in tex
    assert r"\usepackage[french]{babel}" in tex
    assert "(\\textit{en cours})" in tex
    assert "\\section{Projets Data}" in tex


def test_cv_in_english_uses_english_texts(profile, datavia_spec):
    spec = Spec.model_validate({**datavia_spec.model_dump(), "lang": "en", "projects_title": None})
    tex = render_cv(profile, spec)
    assert r"\usepackage[english]{babel}" in tex
    assert r"\section{Professional Experience}" in tex
    assert "Data Analyst (internship)" in tex


def test_cv_refuses_a_spec_the_profile_does_not_back(profile, datavia_spec):
    spec = Spec.model_validate({**datavia_spec.model_dump(), "experiences": ["ghost"]})
    with pytest.raises(SpecError, match="ghost"):
        render_cv(profile, spec)


@pytest.mark.parametrize(
    ("day", "lang", "expected"),
    [
        (date(2027, 9, 1), Lang.FR, "Lyon, le 1er septembre 2027"),
        (date(2027, 8, 14), Lang.FR, "Lyon, le 14 août 2027"),
        (date(2027, 3, 2), Lang.EN, "Lyon, March 2, 2027"),
    ],
)
def test_letter_date(day, lang, expected):
    assert letter_date(day, lang, "Lyon") == expected


def test_letter_paragraphs_and_defaults(profile):
    letter = Letter(
        recipient=["Acme", "RH"], subject="Candidature", body="Un.\n\n  \nDeux & trois."
    )
    tex = render_lm(profile, letter, Lang.FR, date(2027, 9, 1))
    assert "Un.\n\nDeux \\& trois.\n" in tex
    assert "Madame, Monsieur," in tex
    assert "Lyon, le 1er septembre 2027" in tex


def test_leading_bracket_in_a_line_is_escaped(profile, datavia_spec):
    spec = Spec.model_validate({**datavia_spec.model_dump(), "summary": "[Mention] *bien*"})
    assert "{[}Mention{]} {*}bien{*}" in render_cv(profile, spec)
