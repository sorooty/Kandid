"""Applications sent before Kandid, imported once from a JSON file in the user's data folder."""

from datetime import UTC, date, datetime, time
from pathlib import Path

from pydantic import BaseModel, TypeAdapter, field_validator
from sqlalchemy import Engine
from sqlmodel import Session, col, or_, select

from kandid_tools.config import ContractKind
from kandid_tools.db import Application, Event, Offer, now, session
from kandid_tools.dedup import fingerprint
from kandid_tools.files import read_text
from kandid_tools.profile import Strict, Term
from kandid_tools.status import LABELS, Status
from kandid_tools.watch import MANUAL

_BY_LABEL = {label.lower(): status for status, label in LABELS.items()}


class PastApplication(Strict):
    company: Term
    title: Term
    status: Status
    # The day it was sent (or prepared, for an application still "Prêt").
    sent_on: date | None = None
    url: str | None = None
    location: str | None = None
    contract: ContractKind | None = None
    contact: str = ""
    notes: str = ""

    @field_validator("status", mode="before")
    @classmethod
    def _french_label(cls, value: object) -> object:
        # People write "Envoyée" or "Refus" in their own files; the CLI speaks "sent", "rejected".
        if isinstance(value, str):
            return _BY_LABEL.get(value.strip().lower(), value)
        return value


class ImportReport(BaseModel):
    added: list[int]
    # Offers the watch had found, left untouched, now carrying the imported status.
    updated: list[int] = []
    skipped: list[str]


def load_history(path: Path) -> list[PastApplication]:
    return TypeAdapter(list[PastApplication]).validate_json(read_text(path))


# Statuses Kandid sets before the user acts: an offer found by the watch and left there was never
# sent through Kandid, so a past application for it brings the real status.
_UNTOUCHED = {Status.TO_REVIEW, Status.TO_PREPARE}


def _existing(db: Session, key: str, external_id: str) -> tuple[Offer, Application] | None:
    query = (
        select(Offer, Application)
        .join(Application, col(Application.offer_id) == col(Offer.id))
        .where(
            or_(
                Offer.fingerprint == key,
                (Offer.source == MANUAL) & (Offer.external_id == external_id),
            )
        )
    )
    row = db.exec(query).first()
    return None if row is None else (row[0], row[1])


def _add_events(db: Session, application_id: int, when: datetime, item: PastApplication) -> None:
    events = [("status", item.status.value), ("note", "importée depuis l'historique")]
    if item.contact:
        events.append(("note", f"contact : {item.contact}"))
    if item.notes:
        events.append(("note", item.notes))
    for kind, detail in events:
        db.add(Event(application_id=application_id, at=when, kind=kind, detail=detail))


def import_history(engine: Engine, items: list[PastApplication]) -> ImportReport:
    """One offer, one application and its dated events per item. An offer the watch found and left
    untouched takes the imported status; any other known item is skipped, so importing the same
    file twice changes nothing."""
    added: list[int] = []
    updated: list[int] = []
    skipped: list[str] = []
    with session(engine) as db:
        for item in items:
            key = fingerprint(item.company, item.title)
            external_id = item.url or key
            when = datetime.combine(item.sent_on, time(12), tzinfo=UTC) if item.sent_on else now()
            existing = _existing(db, key, external_id)
            if existing is not None:
                offer, application = existing
                if application.status in _UNTOUCHED and item.status not in _UNTOUCHED:
                    application.status, application.updated_at = item.status, when
                    db.add(application)
                    assert application.id is not None and offer.id is not None
                    _add_events(db, application.id, when, item)
                    updated.append(offer.id)
                else:
                    skipped.append(f"{item.company} : {item.title}")
                continue
            offer = Offer(source=MANUAL, external_id=external_id, fingerprint=key,
                          company=item.company, title=item.title, location=item.location,
                          contract=item.contract, url=item.url, first_seen=when)  # fmt: skip
            db.add(offer)
            db.flush()
            if offer.id is None:
                raise RuntimeError("identifiant d'offre non attribué")
            application = Application(offer_id=offer.id, status=item.status,
                                      created_at=when, updated_at=when)  # fmt: skip
            db.add(application)
            db.flush()
            if application.id is None:
                raise RuntimeError("identifiant de candidature non attribué")
            _add_events(db, application.id, when, item)
            added.append(offer.id)
        db.commit()
    return ImportReport(added=added, updated=updated, skipped=skipped)
