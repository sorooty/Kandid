"""Thin wrapper over the Poppler command line tools."""

import re
import shutil
import subprocess
from pathlib import Path


class PopplerError(RuntimeError):
    pass


def _run(tool: str, *args: str) -> str:
    executable = shutil.which(tool)
    if executable is None:
        raise PopplerError(f"{tool} introuvable : installez Poppler (pdftotext, pdfinfo, pdffonts)")
    try:
        result = subprocess.run(
            [executable, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise PopplerError(f"{tool} n'a pas fini en 60 s") from error
    if result.returncode != 0:
        first_line = next(iter(result.stderr.strip().splitlines()), "")
        raise PopplerError(f"{tool} a échoué : {first_line}")
    return result.stdout


def page_count(pdf: Path) -> int:
    match = re.search(r"^Pages:\s+(\d+)", _run("pdfinfo", str(pdf)), re.MULTILINE)
    if match is None:
        raise PopplerError(f"nombre de pages illisible : {pdf}")
    return int(match.group(1))


def text(pdf: Path, *, layout: bool = False) -> str:
    args = ["-enc", "UTF-8", *(["-layout"] if layout else []), str(pdf), "-"]
    return _run("pdftotext", *args)


def fonts(pdf: Path) -> str:
    return _run("pdffonts", str(pdf))
