import shutil
import subprocess

import pytest
from pydantic import ValidationError

from kandid_tools.config import Paths
from kandid_tools.files import read_text

from conftest import EXAMPLES


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "utf-16", "cp1252"])
def test_read_text_accepts_windows_encodings(tmp_path, encoding):
    path = tmp_path / "offre.txt"
    path.write_text("Société, août, 15 %", encoding=encoding)
    assert read_text(path) == "Société, août, 15 %"


@pytest.mark.skipif(shutil.which("git") is None, reason="git requis")
def test_user_documents_are_ignored_by_git_outside_examples():
    root = EXAMPLES.parent
    ignored = [
        "profile.yaml",
        "data/applications/1/spec.yaml",
        "CV/ALTERNANCE/CV_A_B_C_Alternance_D_FR_2027-09.tex",
        "CV/ALTERNANCE/CV_A_B_C_Alternance_D_FR_2027-09.pdf",
        "CV/ALTERNANCE/Offre_C_D.txt",
        "somewhere/templates/CV.pdf",
    ]
    kept = ["examples/camille/profile.yaml", "tools/kandid_tools/templates/cv.tex.j2"]
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", *ignored, *kept],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert sorted(result.stdout.split()) == sorted(ignored)


def test_paths_are_expanded_and_must_be_absolute(monkeypatch, tmp_path):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    assert Paths(master="~/CV").master == tmp_path / "CV"
    with pytest.raises(ValidationError, match="chemin absolu"):
        Paths(master="CV/00_MASTER")
