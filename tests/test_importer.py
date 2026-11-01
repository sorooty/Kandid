import shutil
import zipfile

import pytest
from typer.testing import CliRunner

from kandid_tools.cli import app
from kandid_tools.importer import MAX_DOCX_XML, import_cv
from kandid_tools.latex import compile_pdf
from kandid_tools.render_cv import render_cv

TEX = r"""\documentclass{article}
% \section{Commentaire ignoré}
\begin{document}
Camille Martin, Lyon
\section{Expériences professionnelles}
Data Analyst (stage), Lumio Énergie : tableaux de bord Power BI, 15\,\% de gain
\section*{Compétences}
Python, SQL
\end{document}
"""

WORD = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def docx(path, paragraphs: list[str]) -> None:
    body = "".join(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in paragraphs)
    xml = f'<?xml version="1.0"?><w:document xmlns:w="{WORD}"><w:body>{body}</w:body></w:document>'
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", xml)


def titles(cv) -> list[str]:
    return [section.title for section in cv.sections]


def test_tex_sections_skip_comments_and_unescape(tmp_path):
    path = tmp_path / "cv.tex"
    path.write_text(TEX, encoding="utf-8")
    cv = import_cv(path)
    assert titles(cv) == ["", "Expériences professionnelles", "Compétences"]
    assert "15" in cv.sections[1].text
    assert "Commentaire" not in cv.model_dump_json()


def test_docx_headings_by_name_or_capitals(tmp_path):
    path = tmp_path / "cv.docx"
    docx(path, ["Camille Martin", "Formation", "BUT Science des Données", "LANGUES", "Anglais B2"])
    cv = import_cv(path)
    assert titles(cv) == ["", "Formation", "LANGUES"]
    assert cv.sections[2].text == "Anglais B2"


def test_oversized_or_broken_docx_is_refused(tmp_path):
    big = tmp_path / "big.docx"
    with zipfile.ZipFile(big, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", "a" * (MAX_DOCX_XML + 1))
    with pytest.raises(ValueError, match="trop volumineux"):
        import_cv(big)
    broken = tmp_path / "broken.docx"
    broken.write_bytes(b"not a zip")
    with pytest.raises(ValueError, match="illisible"):
        import_cv(broken)


def test_other_formats_are_refused(tmp_path):
    path = tmp_path / "cv.odt"
    path.write_bytes(b"")
    with pytest.raises(ValueError, match="format non pris en charge"):
        import_cv(path)


@pytest.mark.skipif(
    not (shutil.which("pdflatex") and shutil.which("pdftotext")), reason="pdflatex, Poppler requis"
)
def test_pdf_of_a_rendered_cv(tmp_path, profile, datavia_spec):
    tex = tmp_path / "cv.tex"
    tex.write_text(render_cv(profile, datavia_spec), encoding="utf-8")
    cv = import_cv(compile_pdf(tex))
    assert "Formation" in titles(cv)
    assert any("Lumio" in section.text for section in cv.sections)


def test_cli_prints_json(tmp_path):
    path = tmp_path / "cv.tex"
    path.write_text(TEX, encoding="utf-8")
    result = CliRunner().invoke(app, ["importer", str(path)])
    assert result.exit_code == 0, result.output
    assert '"format": "tex"' in result.stdout
