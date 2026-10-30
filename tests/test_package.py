import kandid_tools


def test_version_matches_installed_metadata():
    assert kandid_tools.__version__ == "0.1.0"
