import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")


def check(*paths: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    script = ROOT / "scripts" / "check-personal-data.mjs"
    return subprocess.run(
        [NODE, str(script), *paths], cwd=cwd, capture_output=True, text=True, encoding="utf-8"
    )


@pytest.mark.skipif(NODE is None, reason="Node.js absent")
@pytest.mark.parametrize(
    ("path", "content", "refused"),
    [
        ("notes.md", "Écrire à jean.dupont@gmail.com", True),
        ("notes.md", "Tél. 06 12 34 56 78", True),
        ("notes.md", "+33 6 12 34 56 78", True),
        ("notes.md", "contact@example.com, noreply@site.fr", False),
        ("notes.md", "sha256 0612345678abcdef", False),
        ("examples/camille/profile.yaml", "camille@gmail.com 06 12 34 56 78", False),
        ("data/kandid.db", "", True),
        ("profile.yaml", "", True),
        ("sub/.kandid/x.txt", "", True),
        ("tests/fixtures/config.yaml", "", False),
        ("Profile.YAML", "", True),
        ("offres/1/fiche.md", "", True),
        ("docs/CV_Camille.pdf", "", True),
        ("data/kandid.db-journal", "", True),
        (".env.local", "", True),
        ("notes.md", "support@entreprise.fr", True),
        ("assets/readme/illustration.svg", '<svg><path d="M 06 12 34 56 78"/></svg>', False),
        ("assets/readme/illustration.svg", "<svg><text>06 12 34 56 78</text></svg>", True),
    ],
)
def test_personal_data_check(tmp_path, path, content, refused):
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    result = check(path, cwd=tmp_path)
    assert (result.returncode == 1) is refused, result.stderr
