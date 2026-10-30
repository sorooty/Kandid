"""File names and folders of generated documents."""

import re
import unicodedata
from datetime import date
from pathlib import PurePath

from kandid_tools.config import NamingConfig

_PLACEHOLDER = re.compile(r"\{([^{}]*)\}")
_DOC_TYPE = re.compile(r"[A-Za-z]+")
# Letters that NFKD does not split into a base letter plus an accent.
_TRANSLITERATION = str.maketrans(
    {"ø": "o", "Ø": "O", "ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ß": "ss", "æ": "ae",
     "Æ": "AE", "œ": "oe", "Œ": "OE", "'": "", chr(0x2019): ""}
)  # fmt: skip


def _words(text: str) -> list[str]:
    # Apostrophes are dropped, not split on: "O'Brien" stays one word, "l'Oréal" gives "LOreal".
    decomposed = unicodedata.normalize("NFKD", text.translate(_TRANSLITERATION))
    return re.findall(r"[A-Za-z0-9]+", decomposed.encode("ascii", "ignore").decode())


def _non_empty(slug: str, source: str) -> str:
    if not slug:
        raise ValueError(f"aucune lettre utilisable pour un nom de fichier : '{source}'")
    return slug


def _capitalize(word: str) -> str:
    # Only the first letter: acronyms such as "BI" or "ENGIE" keep their case.
    return word[:1].upper() + word[1:]


def company_slug(company: str) -> str:
    """'Société Générale' gives 'SocieteGenerale'."""
    return "".join(_capitalize(w) for w in _words(company))


def role_slug(role: str) -> str:
    """'Data analyst / BI' gives 'Data-Analyst-BI'. Also used for person names."""
    return "-".join(_capitalize(w) for w in _words(role))


def fill(template: str, values: dict[str, str]) -> str:
    """Replace `{name}` placeholders. Unlike str.format, gives no access to attributes."""

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            raise ValueError(f"variable inconnue dans le motif : {{{key}}}")
        return values[key]

    return _PLACEHOLDER.sub(replace, template)


def document_name(
    config: NamingConfig,
    *,
    doc: str,
    first_name: str,
    last_name: str,
    company: str,
    contract: str,
    role: str,
    lang: str,
    month: date,
) -> str:
    if contract not in config.contracts:
        raise ValueError(
            f"contrat inconnu : '{contract}' (attendu : {', '.join(config.contracts)})"
        )
    if not _DOC_TYPE.fullmatch(doc):
        raise ValueError(f"type de document invalide : '{doc}' (lettres seulement)")
    return fill(
        config.pattern,
        {
            "doc": doc,
            "first": _non_empty(role_slug(first_name), first_name),
            "last": _non_empty(role_slug(last_name), last_name),
            "company": _non_empty(company_slug(company), company),
            "contract": contract,
            "role": _non_empty(role_slug(role), role),
            "lang": lang.upper(),
            "month": month.strftime("%Y-%m"),
        },
    )


def document_folder(config: NamingConfig, *, doc: str, contract: str) -> PurePath:
    folder = config.contract_folders.get(contract, config.other_folder)
    layout = config.layout.get(doc, "{folder}")
    return PurePath(*fill(layout, {"folder": folder}).split("/"))
