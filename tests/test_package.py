import kandid_tools


def test_version_is_exposed():
    assert isinstance(kandid_tools.__version__, str)
    assert kandid_tools.__version__
