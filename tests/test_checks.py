"""ATS, wrapcheck and honesty logic on plain text, without Poppler."""

from kandid_tools.ats import format_checks, offer_keywords
from kandid_tools.honesty import IssueKind, check_text, untex
from kandid_tools.wrapcheck import wrapped_lines

from conftest import EXAMPLES


def test_wrapped_label_rows_are_flagged():
    layout = """Formation
Université Lumière Lyon 2 -- Bron                       2027 -- 2029
Compétences
Langages : Python, SQL
Machine Learning : Scikit-learn, régression,
classification
Certifications
Obtenues : PIX
Savoir-être
Hobbies : Escalade"""
    assert wrapped_lines(layout) == ["classification"]


def test_english_sections_are_checked_too():
    assert wrapped_lines("Skills\nLanguages: Python\nwrapped tail") == ["wrapped tail"]


def test_offer_keywords_ignore_url_and_company():
    offer = (EXAMPLES / "offers" / "datavia-data-analyst.txt").read_text(encoding="utf-8")
    keywords = offer_keywords(
        offer, "Python SQL Power BI PostgreSQL qualité des données", "Datavia"
    )
    assert "datavia" not in keywords.found + keywords.missing
    assert not any("example" in k for k in keywords.found + keywords.missing)
    assert "sql" in keywords.found
    assert 0 < keywords.score <= 100


def test_format_checks_score_a_clean_one_column_text():
    raw = (
        "Camille Martin camille@example.com 06 00 00 00 00 Lyon linkedin.com/in/camille\n"
        "Alternance\nExpériences professionnelles\nFormation\nCompétences\nProjets\n"
        + "2024 2025 2026 2027 2028 2029 +6 clients 80 % 15 % 12 heures\n"
        + "mot " * 400
    )
    points, checks = format_checks(raw, raw, "name type\n---- ----\n", 1, ["Lyon"])
    assert points["parsing"] == 40
    assert all(c.level != "KO" for c in checks)


def test_honesty_accepts_profile_facts(profile):
    report = check_text("Python, SQL sur PostgreSQL et Power BI ; PowerBI aussi.", profile)
    assert report.ok
    assert report.issues == []


def test_honesty_blocks_unknown_and_unconfirmed_tools(profile):
    report = check_text("Expérience en Kubernetes et Spark, avec PySpark.", profile)
    assert not report.ok
    kinds = {i.term: i.kind for i in report.issues}
    assert kinds == {
        "Spark": IssueKind.UNCONFIRMED,
        "Kubernetes": IssueKind.UNKNOWN,
        "PySpark": IssueKind.UNKNOWN,
    }


def test_honesty_lets_a_letter_name_an_unconfirmed_tool(profile):
    report = check_text("Je n'ai pas encore pratiqué Spark.", profile, letter=True)
    assert report.ok
    assert [(i.term, i.blocking) for i in report.issues] == [("Spark", False)]


def test_honesty_blocks_forbidden_terms(profile):
    report = check_text("Mon Projet Personnel de prévision.", profile)
    assert [(i.term, i.kind) for i in report.issues] == [("projet personnel", IssueKind.FORBIDDEN)]


def test_honesty_does_not_match_inside_other_words(profile):
    assert check_text("JavaScript", profile).issues == []


def test_wrapped_tail_with_a_colon_is_still_flagged():
    layout = "Compétences\nLangues : Français (natif) ; Anglais\n(niveau : avancé)"
    assert wrapped_lines(layout) == ["(niveau : avancé)"]


def test_forbidden_terms_respect_word_boundaries_and_line_breaks(profile):
    rules = profile.rules.model_copy(update={"forbidden_terms": ["senior", "projet personnel"]})
    strict = profile.model_copy(update={"rules": rules})
    assert check_text("Seniority et projets personnels.", strict).issues == []
    report = check_text("Un projet\npersonnel en Python.", strict)
    assert [i.term for i in report.issues] == ["projet personnel"]


def test_dictionary_words_are_not_tools(profile):
    text = "I hope to excel in a swift and react quickly to git changes, rust aside."
    assert check_text(text, profile).issues == []
    assert [i.term for i in check_text("Backend in Rust.", profile).issues] == ["Rust"]


def test_tex_markup_is_undone_before_checking(profile):
    issues = check_text(untex(r"Outils : C\# et Kubernetes{*}"), profile).issues
    assert {i.term for i in issues} == {"C#", "Kubernetes"}
