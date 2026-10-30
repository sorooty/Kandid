"""What every offer source shares: the offer model, a polite HTTP client, text helpers."""

import html
import logging
import re
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, field_validator

from kandid_tools import __version__
from kandid_tools.config import ContractKind

USER_AGENT = f"Kandid/{__version__} (+https://github.com/sorooty/Kandid)"
TIMEOUT = 20.0
# C0 and C1 control characters, except tab and newline.
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_WEB_URL = re.compile(r"^https?://", re.IGNORECASE)

# httpx logs every URL at INFO level, and Adzuna takes its key in the query string.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


# Company placeholder when a source hides it (anonymous offers): never used to spot duplicates.
UNKNOWN_COMPANY = "?"


class SourceError(RuntimeError):
    """A source failed. The message never contains a secret or a response body."""


class MissingCriteria(SourceError):
    """The search lacks what this source needs (keywords, job codes, companies): not a failure."""


class PartialResult(SourceError):
    """Part of the search failed; the offers read before or beside the failure are kept."""

    def __init__(self, message: str, offers: list["RawOffer"]) -> None:
        super().__init__(message)
        self.offers = offers


class Payload(BaseModel):
    """Base of the response models: unknown fields are ignored, sources add fields over time."""

    model_config = ConfigDict(extra="ignore")


class RawOffer(BaseModel):
    source: str
    external_id: str
    company: str
    title: str
    location: str | None = None
    contract: ContractKind | None = None
    remote: bool | None = None
    url: str | None = None
    description: str = ""
    published_at: datetime | None = None
    # Set by a source that knows the offer was posted by a school or an intermediary.
    intermediary: bool = False

    @field_validator("source", "external_id", "company", "title", "location", "description")
    @classmethod
    def _no_control_chars(cls, value: str | None) -> str | None:
        # Remote text is echoed to a terminal: escape sequences could rewrite what the user sees.
        return _CONTROL.sub("", value) if value else value

    @field_validator("url")
    @classmethod
    def _web_url_only(cls, value: str | None) -> str | None:
        # The app will render it as a link: a `javascript:` URL would run in the page.
        return value if value and _WEB_URL.match(value) else None


def client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        transport=transport,
    )


def request(client: httpx.Client, method: str, url: str, **kwargs: Any) -> httpx.Response:
    """One retry on a network error or a server error; a rate limit stops the source."""
    for attempt in range(2):
        try:
            response = client.request(method, url, **kwargs)
        except httpx.TransportError as error:
            if attempt == 0:
                continue
            raise SourceError(f"réseau indisponible ({type(error).__name__})") from None
        except (httpx.HTTPError, httpx.InvalidURL) as error:
            # `from None` everywhere: a chained httpx error carries the URL, hence the keys.
            raise SourceError(f"requête échouée ({type(error).__name__})") from None
        if response.status_code >= 500 and attempt == 0:
            continue
        if response.status_code == 429:
            raise SourceError("limite de requêtes atteinte, réessayez plus tard")
        if response.status_code in (401, 403):
            raise SourceError(f"accès refusé ({response.status_code}) : vérifiez les identifiants")
        if response.status_code >= 400:
            raise SourceError(f"erreur HTTP {response.status_code}")
        return response
    raise SourceError("erreur serveur persistante")


def json_body(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        raise SourceError("réponse illisible (JSON invalide)") from None


_TAG = re.compile(r"<[^>]+>")
_BLOCK_END = re.compile(r"</(p|li|h\d|div)>|<br\s*/?>", re.IGNORECASE)


def html_to_text(markup: str | None) -> str:
    if not markup:
        return ""
    # Some APIs escape their HTML once more (Greenhouse): unescape until stable, twice at most.
    text = html.unescape(html.unescape(markup))
    text = _BLOCK_END.sub("\n", text)
    text = html.unescape(_TAG.sub("", text))
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


# Order matters: "contrat d'apprentissage en CDD" is a work-study contract first.
_CONTRACT_PATTERNS = [
    (ContractKind.WORK_STUDY, r"altern|apprenti|apprentice|professionnalisation|work[- ]study"),
    (ContractKind.INTERNSHIP, r"\bstages?\b|stagiaire|intern(ship)?\b|praktikum|tirocinio"),
    (ContractKind.FREELANCE, r"freelance|ind[ée]pendant|contractor"),
    (ContractKind.TEMPORARY, r"int[ée]rim|temporary|temp\b"),
    (ContractKind.FIXED_TERM, r"\bcdd\b|fixed[- ]term|contrat [àa] dur[ée]e d[ée]termin"),
    (ContractKind.PERMANENT, r"\bcdi\b|permanent|contrat [àa] dur[ée]e ind[ée]termin"),
]


def classify_contract(*texts: str | None) -> ContractKind | None:
    """Contract family read from labels or titles, in French or English."""
    joined = " ".join(t for t in texts if t).lower()
    for kind, pattern in _CONTRACT_PATTERNS:
        if re.search(pattern, joined):
            return kind
    return None


def parse_datetime(value: str | int | float | None) -> datetime | None:
    """ISO strings, "2026-10-06 14:54:28 UTC" strings or epoch milliseconds."""
    if value is None or value == "":
        return None
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value / 1000, tz=UTC)
    try:
        parsed = datetime.fromisoformat(value.replace(" UTC", "+00:00").replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
