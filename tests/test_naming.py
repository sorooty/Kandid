from datetime import date
from pathlib import PurePath

import pytest

from kandid_tools.config import NamingConfig
from kandid_tools.naming import company_slug, document_folder, document_name, fill, role_slug


@pytest.mark.parametrize(
    ("company", "slug"),
    [
        ("Société Générale", "SocieteGenerale"),
        ("BNP Paribas", "BNPParibas"),
        ("ENGIE", "ENGIE"),
        ("l'Oréal", "LOreal"),
    ],
)
def test_company_slug(company, slug):
    assert company_slug(company) == slug


@pytest.mark.parametrize(
    ("role", "slug"),
    [
        ("Data analyst / BI", "Data-Analyst-BI"),
        ("AI Engineer", "AI-Engineer"),
        ("Ingénieur Cloud & IA", "Ingenieur-Cloud-IA"),
    ],
)
def test_role_slug(role, slug):
    assert role_slug(role) == slug


def test_default_document_name():
    name = document_name(
        NamingConfig(),
        doc="CV",
        first_name="Camille",
        last_name="Martin",
        company="Nordlys Énergie",
        contract="Alternance",
        role="Data Scientist",
        lang="fr",
        month=date(2027, 9, 14),
    )
    assert name == "CV_Camille_Martin_NordlysEnergie_Alternance_Data-Scientist_FR_2027-09"


def test_unknown_contract_is_rejected():
    with pytest.raises(ValueError, match="contrat inconnu"):
        document_name(
            NamingConfig(),
            doc="CV",
            first_name="A",
            last_name="B",
            company="C",
            contract="Bénévolat",
            role="D",
            lang="fr",
            month=date(2027, 1, 1),
        )


def test_fill_gives_no_attribute_access():
    with pytest.raises(ValueError, match="variable inconnue"):
        fill("{doc.__class__}", {"doc": "CV"})


def test_document_folder():
    config = NamingConfig()
    assert document_folder(config, doc="CV", contract="Stage-PFE") == PurePath("CV", "STAGE")
    assert document_folder(config, doc="LM", contract="CDI") == PurePath(
        "LETTRES_MOTIVATION", "AUTRES"
    )
    assert document_folder(config, doc="Offre", contract="Alternance") == PurePath("ALTERNANCE")


@pytest.mark.parametrize(
    ("text", "slug"),
    [("Søren Łukasz", "Soren-Lukasz"), ("O'Brien", "OBrien"), ("Straße", "Strasse")],
)
def test_letters_without_decomposition_are_transliterated(text, slug):
    assert role_slug(text) == slug


def _name(**overrides):
    values = {
        "doc": "CV",
        "first_name": "Camille",
        "last_name": "Martin",
        "company": "Acme",
        "contract": "Alternance",
        "role": "Dev",
        "lang": "fr",
        "month": date(2027, 1, 1),
    }
    return document_name(NamingConfig(), **{**values, **overrides})


def test_empty_slug_is_rejected():
    with pytest.raises(ValueError, match="aucune lettre"):
        _name(company="株式会社")


def test_document_type_is_letters_only():
    with pytest.raises(ValueError, match="type de document"):
        _name(doc="../x")
