from pathlib import Path

import pytest
from pydantic import ValidationError

from kandid_tools.spec import Spec, load_spec, spec_errors

from conftest import CAMILLE

BASE = {"offer": {"company": "Acme", "role": "Data Analyst"}, "contract": "Alternance"}


@pytest.mark.parametrize("path", sorted((CAMILLE / "specs").glob("*.yaml")), ids=lambda p: p.stem)
def test_example_specs_are_backed_by_the_profile(path: Path, profile):
    assert spec_errors(load_spec(path), profile) == []


def test_bare_ids_mean_default_wording():
    spec = Spec.model_validate({**BASE, "experiences": ["lumio", {"id": "verde", "wording": "x"}]})
    assert [(p.id, p.wording) for p in spec.experiences] == [("lumio", "default"), ("verde", "x")]


def test_at_least_one_experience():
    with pytest.raises(ValidationError):
        Spec.model_validate({**BASE, "experiences": []})


def test_unknown_items_are_reported(profile):
    spec = Spec.model_validate(
        {
            **BASE,
            "experiences": ["ghost", {"id": "lumio", "wording": "invented"}],
            "projects": ["nope"],
            "skills": ["magic"],
        }
    )
    assert spec_errors(spec, profile) == [
        "expérience inconnue : 'ghost'",
        "formulation inconnue pour l'expérience 'lumio' : 'invented'",
        "projet inconnu : 'nope'",
        "groupe de compétences inconnu : 'magic'",
    ]
