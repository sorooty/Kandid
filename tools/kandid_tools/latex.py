"""LaTeX escaping, Jinja2 environment and pdflatex compilation."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from jinja2 import Environment, PackageLoader, StrictUndefined

_SPECIALS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    # Brackets and stars right after \\ or \item would be read as an optional argument.
    "[": "{[}",
    "]": "{]}",
    "*": "{*}",
}
_SPECIAL_RE = re.compile("|".join(re.escape(c) for c in _SPECIALS))
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


class Tex(str):
    """Text already safe to paste in LaTeX."""


def _escape_plain(text: str) -> str:
    return _SPECIAL_RE.sub(lambda m: _SPECIALS[m.group(0)], text)


def escape(text: str) -> Tex:
    """Escape LaTeX specials and turn the one markup users write, `**bold**`, into textbf."""
    # split() puts the bold captures at odd indexes.
    parts = _BOLD_RE.split(text)
    return Tex(
        "".join(
            rf"\textbf{{{_escape_plain(part)}}}" if i % 2 else _escape_plain(part)
            for i, part in enumerate(parts)
        )
    )


def escape_url(url: str) -> Tex:
    """Escape a link target for \\href, which takes `_` and `~` as is."""
    if not re.fullmatch(r"(https?://|mailto:)[^\s\\{}^$|]+", url):
        raise ValueError(f"lien invalide : {url}")
    return Tex(url.replace("%", r"\%").replace("#", r"\#"))


def _finalize(value: object) -> str:
    # Every value printed by a template is escaped unless it is already Tex: profile and
    # offer text can never inject LaTeX commands.
    return value if isinstance(value, Tex) else escape(str(value))


def environment() -> Environment:
    env = Environment(
        loader=PackageLoader("kandid_tools", "templates"),
        block_start_string="((*",
        block_end_string="*))",
        variable_start_string="(((",
        variable_end_string=")))",
        comment_start_string="((#",
        comment_end_string="#))",
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=False,
        undefined=StrictUndefined,
        finalize=_finalize,
    )
    env.filters["url"] = escape_url
    return env


class LatexError(RuntimeError):
    pass


def _failure_message(log: str, tex_path: Path) -> str:
    """Error lines and line number only: the rest of the log quotes the source, i.e. CV text."""
    # Some error lines quote the offending text: keep only their start.
    errors = [line[:80] for line in log.splitlines() if line.startswith("!")]
    line_numbers = re.findall(r"^l\.(\d+)", log, re.MULTILINE)
    where = f" (ligne {line_numbers[0]} de {tex_path.name})" if line_numbers else ""
    return f"échec de pdflatex{where} :\n" + "\n".join(errors[:3])


def compile_pdf(tex_path: Path, timeout: float = 120) -> Path:
    """Compile `tex_path` and put the PDF next to it. Aux and log files stay in a temp folder."""
    pdflatex = shutil.which("pdflatex")
    if pdflatex is None:
        raise LatexError(
            "pdflatex introuvable : installez une distribution LaTeX (MiKTeX, TeX Live)"
        )
    with tempfile.TemporaryDirectory() as build:
        try:
            result = subprocess.run(
                [
                    pdflatex,
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "-no-shell-escape",
                    f"-output-directory={build}",
                    str(tex_path),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise LatexError(f"pdflatex n'a pas fini en {timeout:.0f} s") from error
        built = Path(build) / f"{tex_path.stem}.pdf"
        if result.returncode != 0 or not built.exists():
            raise LatexError(_failure_message(result.stdout, tex_path))
        pdf_path = tex_path.with_suffix(".pdf")
        shutil.move(built, pdf_path)
    return pdf_path
