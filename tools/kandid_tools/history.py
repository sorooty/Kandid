"""Applications sent before Kandid, imported once from a JSON file in the user's data folder."""

from datetime import UTC, date, datetime, time
from pathlib import Path

from pydantic import BaseModel, TypeAdapter, field_validator
from sqlalchemy import Engine
from sqlmodel import Session, or_, select

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
    skipped: list[str]


def load_history(path: Path) -> list[PastApplication]:
    return TypeAdapter(list[PastApplication]).validate_json(read_text(path))


def _known(db: Session, key: str, external_id: str) -> bool:
    query = select(Offer.id).where(
        or_(
            Offer.fingerprint == key,
            (Offer.source == MANUAL) & (Offer.external_id == external_id),
        )
    )
    return db.exec(query).first() is not None


def import_history(engine: Engine, items: list[PastApplication]) -> ImportReport:
    """One offer, one application and its dated events per item; an item already known is skipped,
    so importing the same file twice changes nothing."""
    added: list[int] = []
    skipped: list[str] = []
    with session(engine) as db:
        for item in items:
            key = fingerprint(item.company, item.title)
            external_id = item.url or key
            if _known(db, key, external_id):
                skipped.append(f"{item.company} : {item.title}")
                continue
            when = datetime.combine(item.sent_on, time(12), tzinfo=UTC) if item.sent_on else now()
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
            events = [("status", item.status.value), ("note", "importée depuis l'historique")]
            if item.contact:
                events.append(("note", f"contact : {item.contact}"))
            if item.notes:
                events.append(("note", item.notes))
            for kind, detail in events:
                db.add(Event(application_id=application.id, at=when, kind=kind, detail=detail))
            added.append(offer.id)
        db.commit()
    return ImportReport(added=added, skipped=skipped)
