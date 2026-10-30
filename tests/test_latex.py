import pytest

from kandid_tools.latex import Tex, environment, escape, escape_url


def test_escape_specials():
    assert escape("R&D à 100% pour C# {x}") == r"R\&D à 100\% pour C\# \{x\}"
    assert escape(r"a\b ~ ^") == r"a\textbackslash{}b \textasciitilde{} \textasciicircum{}"


def test_escape_turns_double_stars_into_bold():
    assert escape("gain de **80%**") == r"gain de \textbf{80\%}"


def test_templates_cannot_inject_latex():
    template = environment().from_string("(((value))) (((safe)))")
    rendered = template.render(value=r"\input{/etc/passwd}", safe=Tex(r"\textbf{ok}"))
    assert rendered == r"\textbackslash{}input\{/etc/passwd\} \textbf{ok}"


def test_escape_url():
    assert escape_url("https://example.com/a_b#top?x=1%") == r"https://example.com/a_b\#top?x=1\%"
    for bad in ("javascript:alert(1)", r"https://x.com/\input{y}", "ftp://x"):
        with pytest.raises(ValueError):
            escape_url(bad)


def test_escape_neutralizes_optional_argument_openers():
    # After \ or \item, a leading [ or * would be read as an argument.
    assert escape("[2026] *note*") == "{[}2026{]} {*}note{*}"


def test_bold_content_is_escaped_too():
    assert escape("**R&D [x]**") == r"\textbf{R\&D {[}x{]}}"


def test_escape_url_rejects_trailing_newline_and_hyperref_breakers():
    for bad in ("https://a.com\n", "https://a.com/a|b", "https://a.com/^x"):
        with pytest.raises(ValueError):
            escape_url(bad)
