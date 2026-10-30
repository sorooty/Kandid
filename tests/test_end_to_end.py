"""Real renders of Camille's documents: skipped when pdflatex or Poppler is missing."""

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from kandid_tools import pdftools, wrapcheck
from kandid_tools.cli import app
from kandid_tools.latex import LatexError, compile_pdf

from conftest import CAMILLE, EXAMPLES

pytestmark = pytest.mark.skipif(
    shutil.which("pdflatex") is None or shutil.which("pdftotext") is None,
    reason="pdflatex et Poppler requis",
)

runner = CliRunner()
PROFILE = str(CAMILLE / "profile.yaml")
SPECS = sorted((CAMILLE / "specs").glob("*.yaml"))


def _render_cv(spec: Path, out: Path) -> Path:
    result = runner.invoke(
        app,
        ["render", "cv", PROFILE, str(spec), "--out", str(out), "--date", "2027-09-01", "--json"],
    )
    assert result.exit_code == 0, result.output
    return Path(json.loads(result.stdout)["pdf"])


@pytest.mark.parametrize("spec", SPECS, ids=lambda p: p.stem)
def test_cv_is_one_page_without_wrapped_labels_nor_unknown_claims(spec, tmp_path):
    pdf = _render_cv(spec, tmp_path)
    assert pdftools.page_count(pdf) == 1
    assert wrapcheck.check(pdf) == []
    result = runner.invoke(app, ["honesty", PROFILE, str(pdf)])
    assert result.exit_code == 0, result.output


def test_cv_scores_well_on_ats(tmp_path):
    pdf = _render_cv(CAMILLE / "specs" / "datavia.yaml", tmp_path)
    offer = EXAMPLES / "offers" / "datavia-data-analyst.txt"
    result = runner.invoke(
        app,
        [
            "ats",
            str(pdf),
            "--offer",
            str(offer),
            "--company",
            "Datavia",
            "--profile",
            PROFILE,
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["parsing"] == 40
    assert report["format_score"] >= 90


def test_letter_is_dated_and_honest(tmp_path):
    result = runner.invoke(
        app,
        [
            "render", "lm", PROFILE, str(CAMILLE / "specs" / "datavia.yaml"),
            str(CAMILLE / "letters" / "datavia.yaml"), "--out", str(tmp_path),
            "--date", "2027-09-01", "--json",
        ],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    pdf = Path(json.loads(result.stdout)["pdf"])
    assert pdf.name == "LM_Camille_Martin_Datavia_Alternance_Data-Analyst_FR_2027-09.pdf"
    assert "le 1er septembre 2027" in pdftools.text(pdf)
    assert runner.invoke(app, ["honesty", PROFILE, str(pdf), "--letter"]).exit_code == 0


def test_honesty_fails_on_a_letter_with_invented_tools(tmp_path):
    letter = tmp_path / "letter.txt"
    letter.write_text("J'ai déployé des modèles sur Kubernetes avec Spark.", encoding="utf-8")
    result = runner.invoke(app, ["honesty", PROFILE, str(letter), "--json"])
    assert result.exit_code == 1
    terms = {i["term"] for i in json.loads(result.stdout)["issues"]}
    assert terms == {"Kubernetes", "Spark"}


def test_failed_compile_does_not_echo_source_text(tmp_path):
    tex = tmp_path / "broken.tex"
    tex.write_text(
        "\\documentclass{article}\\begin{document}\nSENTINEL \\undefinedcommand\n\\end{document}\n",
        encoding="utf-8",
    )
    with pytest.raises(LatexError) as error:
        compile_pdf(tex)
    assert "Undefined control sequence" in str(error.value)
    assert "ligne 2" in str(error.value)
    assert "SENTINEL" not in str(error.value)
