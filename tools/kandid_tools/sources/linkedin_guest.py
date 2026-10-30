"""LinkedIn job search as a logged-out visitor sees it. Off by default (ADR 0013): LinkedIn's terms
forbid automated access, so the user enables it knowingly.

The endpoint returns HTML cards, ten or so per page; the card classes below are those of the
public pages and are checked on the first real run. Search results carry no description.
Requests are spaced out and a rate limit ends the run with what was already read.
"""

import time
from html.parser import HTMLParser

import httpx

from kandid_tools.config import WatchConfig
from kandid_tools.sources.base import (
    UNKNOWN_COMPANY,
    MissingCriteria,
    PartialResult,
    RawOffer,
    SourceError,
    classify_contract,
    parse_datetime,
    request,
)

NAME = "linkedin_guest"
URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
PAUSE = 1.5
MAX_PAGES = 4
_URN = "urn:li:jobPosting:"
_FIELDS = {
    "base-search-card__title": "title",
    "base-search-card__subtitle": "company",
    "job-search-card__location": "location",
}


class _CardParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.cards: list[dict[str, str]] = []
        self._field: str | None = None
        self._field_tag = ""
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        urn = values.get("data-entity-urn", "")
        if urn.startswith(_URN):
            self.cards.append({"id": urn.removeprefix(_URN)})
        if not self.cards:
            return
        card = self.cards[-1]
        classes = values.get("class", "").split()
        href = values.get("href", "")
        if href and ("base-card__full-link" in classes or urn.startswith(_URN)):
            card.setdefault("url", href.split("?")[0])
        if tag == "time" and values.get("datetime"):
            card["date"] = values["datetime"]
        field = next((f for c, f in _FIELDS.items() if c in classes), None)
        if field and self._field is None:
            self._field, self._field_tag, self._text = field, tag, []

    def handle_data(self, data: str) -> None:
        if self._field:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._field and tag == self._field_tag:
            self.cards[-1][self._field] = " ".join("".join(self._text).split())
            self._field = None


def _parse(markup: str) -> list[RawOffer]:
    parser = _CardParser()
    parser.feed(markup)
    return [
        RawOffer(
            source=NAME,
            external_id=card["id"],
            company=card.get("company") or UNKNOWN_COMPANY,
            title=card["title"],
            location=card.get("location"),
            contract=classify_contract(card["title"]),
            url=card.get("url") or f"https://www.linkedin.com/jobs/view/{card['id']}",
            published_at=parse_datetime(card.get("date")),
        )
        for card in parser.cards
        if card.get("title")
    ]


def covers_area(watch: WatchConfig) -> bool:
    return bool(watch.area.city)


def search(client: httpx.Client, watch: WatchConfig, secrets: dict[str, str]) -> list[RawOffer]:
    if not watch.keywords:
        raise MissingCriteria("aucun mot-clé dans watch.keywords : LinkedIn cherche par mots-clés")
    offers: dict[str, RawOffer] = {}
    first_request = True
    for keyword in watch.keywords:
        params: dict[str, str | int] = {
            "keywords": keyword,
            "f_TPR": f"r{watch.max_age_days * 86400}",
        }
        if watch.area.city:
            params["location"] = watch.area.city
        start = 0
        for _ in range(MAX_PAGES):
            if not first_request:
                time.sleep(PAUSE)
            first_request = False
            try:
                response = request(client, "GET", URL, params=params | {"start": start})
            except SourceError as error:
                if offers:
                    raise PartialResult(str(error), list(offers.values())) from None
                raise
            found = _parse(response.text)
            if not found:
                break
            start += len(found)
            offers |= {o.external_id: o for o in found}
    return list(offers.values())
