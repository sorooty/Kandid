"""Reading user files, whatever Windows tool wrote them."""

import codecs
import os
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


def _key(path: Path) -> str:
    # Resolved (no "..", links followed) and case-folded as Windows compares paths.
    return os.path.normcase(str(path.resolve()))


def is_inside(path: Path, folder: Path) -> bool:
    """Whether `path` is `folder` or lies under it, whatever the spelling: case, "..", but also a
    long path prefix, a loopback share, an 8.3 short name or a junction, caught by comparing the
    existing ancestors of `path` with the folder itself."""
    target, root = _key(path), _key(folder)
    if target == root or target.startswith(root.rstrip("\\/") + os.sep):
        return True
    try:
        folder_stat = folder.stat()
    except OSError:
        return False
    # Some virtual drives report no file index; equal zeros would make every folder the same.
    if not folder_stat.st_ino:
        return False
    for candidate in (path.resolve(), *path.resolve().parents):
        try:
            if os.path.samestat(candidate.stat(), folder_stat):
                return True
        except OSError:
            continue
    return False
