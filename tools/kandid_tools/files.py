"""Reading user files, whatever Windows tool wrote them."""

import codecs
from pathlib import Path
from typing import Any

import yaml


def read_text(path: Path) -> str:
    """UTF-8 first. PowerShell redirections write UTF-16 with a BOM, and Notepad or Excel exports
    may still be in cp1252, so those are accepted too."""
    data = path.read_bytes()
    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(read_text(path))
