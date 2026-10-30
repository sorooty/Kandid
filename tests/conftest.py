from pathlib import Path

import pytest

from kandid_tools.profile import Profile, load_profile
from kandid_tools.spec import Spec, load_spec

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
CAMILLE = EXAMPLES / "camille"


@pytest.fixture(autouse=True)
def _isolated_home(monkeypatch, tmp_path_factory):
    # The CLI falls back on ~/.kandid: tests must never touch the developer's real data.
    monkeypatch.setenv("KANDID_HOME", str(tmp_path_factory.mktemp("kandid")))


@pytest.fixture(scope="session")
def profile() -> Profile:
    return load_profile(CAMILLE / "profile.yaml")


@pytest.fixture(scope="session")
def datavia_spec() -> Spec:
    return load_spec(CAMILLE / "specs" / "datavia.yaml")


@pytest.fixture(scope="session")
def profile_data() -> dict:
    """Raw profile dict, for tests that build invalid variants."""
    return load_profile(CAMILLE / "profile.yaml").model_dump(mode="json")
