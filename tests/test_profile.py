import copy

import pytest
from pydantic import ValidationError

from kandid_tools.profile import Lang, MissingTranslationError, Profile, localize


def test_example_profile_loads(profile):
    assert profile.identity.first_name == "Camille"
    assert profile.rules.default_project == "meteo"


def test_localize():
    assert localize("Python", Lang.EN) == "Python"
    assert localize({"fr": "Rigueur", "en": "Rigour"}, Lang.EN) == "Rigour"
    with pytest.raises(MissingTranslationError):
        localize({"fr": "Rigueur"}, Lang.EN)


def test_unknown_field_is_rejected(profile_data):
    data = copy.deepcopy(profile_data)
    data["identity"]["nickname"] = "Cam"
    with pytest.raises(ValidationError):
        Profile.model_validate(data)


def test_experience_needs_a_default_wording(profile_data):
    data = copy.deepcopy(profile_data)
    data["experiences"][0]["wordings"] = {"ml": ["..."]}
    with pytest.raises(ValidationError, match="default"):
        Profile.model_validate(data)


def test_duplicate_ids_are_rejected(profile_data):
    data = copy.deepcopy(profile_data)
    data["projects"].append(data["projects"][0])
    with pytest.raises(ValidationError, match="en double"):
        Profile.model_validate(data)


def test_default_project_must_exist(profile_data):
    data = copy.deepcopy(profile_data)
    data["rules"]["default_project"] = "missing"
    with pytest.raises(ValidationError, match="default_project"):
        Profile.model_validate(data)


def test_fact_texts_leave_rules_out(profile):
    facts = "\n".join(profile.fact_texts())
    assert "Power BI" in facts
    assert "Spark" not in facts


def test_empty_rule_terms_are_rejected(profile_data):
    data = copy.deepcopy(profile_data)
    data["rules"]["forbidden_terms"] = ["  "]
    with pytest.raises(ValidationError):
        Profile.model_validate(data)
