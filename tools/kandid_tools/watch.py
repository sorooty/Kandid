"""`kandid veille`: query the enabled sources, keep real matches, store new offers in "À voir"."""

import re
from datetime import datetime
from typing import Protocol

import httpx
from pydantic import BaseModel
from sqlalchemy import Engine
from sqlmodel import Session, col, select

from kandid_tools.ats import norm
from kandid_tools.config import Area, Config, WatchConfig, secrets_for
from kandid_tools.db import Application, Event, Offer, Run, now, session
from kandid_tools.dedup import fingerprint
from kandid_tools.honesty import phrase_pattern
from kandid_tools.scoring import Score, score
from kandid_tools.sources import adzuna, careers, francetravail, labonnealternance, linkedin_guest
from kandid_tools.sources.base import (
    UNKNOWN_COMPANY,
    MissingCriteria,
    PartialResult,
    RawOffer,
    SourceError,
    client,
)


class Source(Protocol):
    NAME: str

    def search(
        self, client: httpx.Client, watch: WatchConfig, secrets: dict[str, str]
    ) -> list[RawOffer]: ...

    def covers_area(self, watch: WatchConfig) -> bool: ...


# Order matters: when two sources carry the same offer, the first one keeps it. A company's own
# board comes first, then public services, then aggregators.
SOURCES: dict[str, Source] = {
    s.NAME: s for s in (careers, labonnealternance, francetravail, adzuna, linkedin_guest)
}
MANUAL = "manuel"


class SourceReport(BaseModel):
    fetched: int = 0
    kept: int = 0
    duplicates: int = 0
    filtered: int = 0
    skipped: str | None = None
    error: str | None = None


class NewOffer(BaseModel):
    id: int | None
    source: str
    company: str
    title: str
    score: int
    url: str | None


class WatchReport(BaseModel):
    run_id: int | None
    dry_run: bool
    sources: dict[str, SourceReport]
    new: list[NewOffer]


def area_match(offer: RawOffer, area: Area, covered: bool) -> bool | None:
    """True when the offer is in the wanted area, None when its location is unknown."""
    if covered or (offer.remote and area.remote) or not (area.city or area.departements):
        return True
    if not offer.location:
        return None
    location = norm(offer.location)
    if area.city and phrase_pattern(area.city).search(location):
        return True
    return any(_department(code.lower()).search(location) for code in area.departements)


def _department(code: str) -> re.Pattern[str]:
    # "(75)", "75 - Paris" or a postal code starting with the code ("75011", "97100"), but not
    # any number: "Paris 15e" is not in the Cantal.
    postal = rf"(?<!\d){code}\d{{{5 - len(code)}}}(?!\d)" if code.isdigit() else "(?!)"
    return re.compile(rf"\({code}\)|^{code}\s*-|{postal}")


def _rejection(offer: RawOffer, watch: WatchConfig, in_area: bool | None, today: datetime) -> bool:
    if watch.contracts and offer.contract and offer.contract not in watch.contracts:
        return True
    # Title only: excluded words such as "senior" often appear in descriptions of junior posts.
    title = norm(offer.title)
    if any(phrase_pattern(word).search(title) for word in watch.exclude):
        return True
    if offer.published_at and (today - offer.published_at).days > watch.max_age_days:
        return True
    return in_area is False


class _Store:
    """Offers already known, from the database and from this run, to drop duplicates."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.fingerprints: dict[str, list[Offer]] = {}

    def seen(self, source: str, offers: list[RawOffer]) -> set[str]:
        ids = [o.external_id for o in offers]
        query = select(Offer.external_id).where(
            Offer.source == source, col(Offer.external_id).in_(ids)
        )
        return set(self.db.exec(query).all())

    def same_offers(self, key: str) -> list[Offer]:
        if key not in self.fingerprints:
            found = self.db.exec(select(Offer).where(Offer.fingerprint == key)).all()
            self.fingerprints[key] = list(found)
        return self.fingerprints[key]


def _is_duplicate(existing: Offer, offer: RawOffer) -> bool:
    # Across sources, company and title are enough. Within one source, the same title in two
    # places is two offers.
    if existing.source != offer.source:
        return True
    return norm(existing.location or "") == norm(offer.location or "")


def _link_duplicate(existing: Offer, offer: RawOffer, dry_run: bool) -> None:
    if dry_run or existing.source == offer.source:
        return
    link = {"source": offer.source, "url": offer.url or ""}
    if link not in existing.also_on:
        # A new list, so that SQLAlchemy sees the JSON column change.
        existing.also_on = [*existing.also_on, link]


def _insert(db: Session, offer: RawOffer, key: str, run_id: int | None, scored: Score) -> Offer:
    row = Offer(
        source=offer.source,
        external_id=offer.external_id,
        fingerprint=key,
        company=offer.company,
        title=offer.title,
        location=offer.location,
        contract=offer.contract.value if offer.contract else None,
        url=offer.url,
        description=offer.description,
        published_at=offer.published_at,
        run_id=run_id,
        **scored.model_dump(),
    )
    db.add(row)
    db.flush()
    if row.id is None:
        raise RuntimeError("identifiant d'offre non attribué")
    application = Application(offer_id=row.id)
    db.add(application)
    db.flush()
    if application.id is None:
        raise RuntimeError("identifiant de candidature non attribué")
    db.add(Event(application_id=application.id, kind="found", detail=f"source : {offer.source}"))
    return row


def _process(
    store: _Store, offers: list[RawOffer], *, covered: bool, watch: WatchConfig,
    skills: list[str], run_id: int | None, dry_run: bool, today: datetime,
) -> tuple[SourceReport, list[NewOffer]]:  # fmt: skip
    report = SourceReport(fetched=len(offers))
    new: list[NewOffer] = []
    seen = store.seen(offers[0].source, offers) if offers else set()
    for offer in offers:
        if offer.external_id in seen:
            report.duplicates += 1
            continue
        seen.add(offer.external_id)
        in_area = area_match(offer, watch.area, covered)
        if _rejection(offer, watch, in_area, today):
            report.filtered += 1
            continue
        key = fingerprint(offer.company, offer.title)
        # Anonymous offers all share the company placeholder: their titles prove nothing.
        known = offer.company != UNKNOWN_COMPANY
        candidates = store.same_offers(key) if known else []
        existing = next((o for o in candidates if _is_duplicate(o, offer)), None)
        if existing is not None:
            report.duplicates += 1
            _link_duplicate(existing, offer, dry_run)
            continue
        scored = score(offer, watch, skills, in_area=in_area, today=today)
        if scored.score < watch.min_score:
            report.filtered += 1
            continue
        if dry_run:
            # Not stored, but known for the rest of the run so other sources see it.
            row = Offer(source=offer.source, external_id=offer.external_id, fingerprint=key,
                        company=offer.company, title=offer.title, location=offer.location,
                        url=offer.url)  # fmt: skip
        else:
            row = _insert(store.db, offer, key, run_id, scored)
        if known:
            store.same_offers(key).append(row)
        report.kept += 1
        new.append(NewOffer(id=row.id, source=offer.source, company=offer.company,
                            title=offer.title, score=scored.score, url=offer.url))  # fmt: skip
    return report, new


def run_watch(
    config: Config, engine: Engine, skills: list[str], *, only: str | None = None,
    dry_run: bool = False, transport: httpx.BaseTransport | None = None,
) -> WatchReport:  # fmt: skip
    """One pass over the sources. A failing source is reported and the others still run."""
    if only is not None and only not in SOURCES:
        raise ValueError(f"source inconnue : {only} (connues : {', '.join(SOURCES)})")
    watch = config.watch
    today = now()
    reports: dict[str, SourceReport] = {}
    new: list[NewOffer] = []
    with session(engine) as db, client(transport) as http:
        run = Run(dry_run=dry_run)
        db.add(run)
        db.commit()
        store = _Store(db)
        for name, source in SOURCES.items():
            if only is not None and name != only:
                continue
            settings = getattr(watch.sources, name)
            secrets = secrets_for(settings)
            if not settings.enabled:
                reports[name] = SourceReport(skipped="désactivée dans config.yaml")
                continue
            if secrets is None:
                missing = ", ".join(settings.env.values())
                reports[name] = SourceReport(skipped=f"identifiants absents ({missing})")
                continue
            error: str | None = None
            try:
                offers = source.search(http, watch, secrets)
            except MissingCriteria as missing:
                reports[name] = SourceReport(skipped=str(missing))
                continue
            except PartialResult as partial:
                offers, error = partial.offers, str(partial)
            except SourceError as failure:
                reports[name] = SourceReport(error=str(failure))
                continue
            except ValueError:
                # Pydantic quotes the payload in its message: only the fact is reported.
                reports[name] = SourceReport(error="réponse inattendue")
                continue
            except Exception as bug:
                # A source bug must not stop the others; its message may hold a URL with a key.
                reports[name] = SourceReport(error=f"erreur interne ({type(bug).__name__})")
                continue
            reports[name], kept = _process(
                store, offers, covered=source.covers_area(watch), watch=watch, skills=skills,
                run_id=run.id, dry_run=dry_run, today=today,
            )  # fmt: skip
            reports[name].error = error
            new += kept
            # One commit per source: a later failure keeps what was already stored.
            db.commit()
        run.finished_at = now()
        run.counts = {name: report.model_dump() for name, report in reports.items()}
        db.commit()
        return WatchReport(run_id=run.id, dry_run=dry_run, sources=reports, new=new)


def add_offer(engine: Engine, offer: RawOffer, watch: WatchConfig, skills: list[str]) -> NewOffer:
    """Store an offer the user brings, scored like the others. Raises if it is already known."""
    with session(engine) as db:
        store = _Store(db)
        key = fingerprint(offer.company, offer.title)
        candidates = store.same_offers(key) if offer.company != UNKNOWN_COMPANY else []
        existing = next((o for o in candidates if _is_duplicate(o, offer)), None)
        if store.seen(offer.source, [offer]) or existing is not None:
            where = f" (offre {existing.id})" if existing is not None else ""
            raise ValueError(f"offre déjà enregistrée{where}")
        in_area = area_match(offer, watch.area, covered=False)
        scored = score(offer, watch, skills, in_area=in_area, today=now())
        row = _insert(db, offer, key, None, scored)
        db.commit()
        return NewOffer(id=row.id, source=offer.source, company=offer.company,
                        title=offer.title, score=scored.score, url=offer.url)  # fmt: skip
