"""Text of an existing CV, cut into sections, so `/setup` can turn it into `profile.yaml`.

Reading only: the master CV folder is never written to. The mapping to profile fields is
Claude's job, validated by the user section by section; this module only extracts what the file
says.
"""

import re
import zipfile
from collections.abc import Callable
from pathlib import Path
from xml.etree import ElementTree

from pydantic import BaseModel

from kandid_tools import honesty, pdftools
from kandid_tools.files import read_text

FORMATS = (".tex", ".pdf", ".docx")
# A CV is a few pages; anything bigger is not one, and a zip bomb is refused before inflating.
MAX_DOCX_XML = 20 * 1024 * 1024
_WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_TEX_SECTION = re.compile(r"\\[A-Za-z]*section\*?\{([^}]*)\}")
_TEX_COMMENT = re.compile(r"(?<!\\)%.*")
# Headings of French and English CVs, matched on a line of their own.
_HEADINGS = re.compile(
    r"^(exp[ée]riences?( professionnelles?)?|formations?|[ée]ducation|parcours|comp[ée]tences"
    r"( techniques)?|skills|projets?( personnels?)?|projects|langues|languages|certifications?"
    r"|centres? d'int[ée]r[êe]ts?|int[ée]r[êe]ts|interests|profil|profile|summary|r[ée]sum[ée]"
    r"|work experience|education|activit[ée]s|engagements?|associati(f|ve)s?|savoir-[êe]tre"
    r"|soft skills)\s*:?$",
    re.IGNORECASE,
)


class Section(BaseModel):
    title: str
    text: str


class ImportedCv(BaseModel):
    format: str
    sections: list[Section]


def _split(lines: list[str], is_heading: Callable[[str], str | None]) -> list[Section]:
    sections = [Section(title="", text="")]
    body: list[list[str]] = [[]]
    for line in lines:
        title = is_heading(line)
        if title:
            sections.append(Section(title=title, text=""))
            body.append([])
        else:
            body[-1].append(line)
    for section, text in zip(sections, body, strict=True):
        section.text = "\n".join(text).strip()
    return [s for s in sections if s.title or s.text]


def _plain_heading(line: str) -> str | None:
    stripped = line.strip()
    if _HEADINGS.match(stripped):
        return stripped.rstrip(" :")
    # Short lines in capitals are headings in most CV layouts.
    letters = [c for c in stripped if c.isalpha()]
    if 3 <= len(letters) <= 40 and len(stripped.split()) <= 4 and stripped.isupper():
        return stripped
    return None


def _from_tex(path: Path) -> list[Section]:
    content = _TEX_COMMENT.sub("", read_text(path))
    begin = content.find(r"\begin{document}")
    lines = content[begin if begin >= 0 else 0 :].splitlines()

    def heading(line: str) -> str | None:
        found = _TEX_SECTION.search(line)
        return honesty.untex(found.group(1)).strip() if found else None

    sections = _split(lines, heading)
    for section in sections:
        section.text = honesty.untex(section.text)
    return sections


def _from_docx(path: Path) -> list[Section]:
    with zipfile.ZipFile(path) as archive:
        info = archive.getinfo("word/document.xml")
        if info.file_size > MAX_DOCX_XML:
            raise ValueError(f"document Word trop volumineux pour un CV : {path.name}")
        # The standard parser does not fetch external entities; size is bounded above.
        root = ElementTree.fromstring(archive.read(info))
    lines = []
    for paragraph in root.iter(f"{_WORD}p"):
        lines.append("".join(node.text or "" for node in paragraph.iter(f"{_WORD}t")))
    return _split(lines, _plain_heading)


def import_cv(path: Path) -> ImportedCv:
    suffix = path.suffix.lower()
    if suffix not in FORMATS:
        raise ValueError(f"format non pris en charge ({suffix}) : .tex, .pdf ou .docx")
    if suffix == ".tex":
        sections = _from_tex(path)
    elif suffix == ".pdf":
        sections = _split(pdftools.text(path).splitlines(), _plain_heading)
    else:
        try:
            sections = _from_docx(path)
        except (zipfile.BadZipFile, KeyError, ElementTree.ParseError):
            raise ValueError(f"document Word illisible : {path.name}") from None
    return ImportedCv(format=suffix.lstrip("."), sections=sections)
