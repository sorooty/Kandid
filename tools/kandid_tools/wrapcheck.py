"""Flags `Label : items` rows that wrap onto a second line in the label sections of a CV."""

import re
from pathlib import Path

from kandid_tools import pdftools
from kandid_tools.render_cv import LABELS

_LABEL_SECTIONS = {
    LABELS[lang][key] for lang in LABELS for key in ("skills", "certifications", "qualities")
}
# A label starts with a letter and holds no parenthesis, so a wrapped tail such as
# "(niveau : avancé)" is not mistaken for a new row.
_LABEL_ROW = re.compile(r"^[^\W\d_][^:()]{1,44}\s?:")


def wrapped_lines(layout_text: str) -> list[str]:
    """Lines of label sections that do not start with a label: they are wrapped rows. The
    template puts the label sections last, so checking runs to the end of the page. Heuristic: a
    wrapped tail that looks like "Word : ..." passes as a new row."""
    section_is_checked = False
    wrapped = []
    for line in layout_text.splitlines():
        stripped = line.strip()
        if stripped in _LABEL_SECTIONS:
            section_is_checked = True
        elif section_is_checked and stripped and not _LABEL_ROW.match(stripped):
            wrapped.append(stripped)
    return wrapped


def check(pdf: Path) -> list[str]:
    return wrapped_lines(pdftools.text(pdf, layout=True))
