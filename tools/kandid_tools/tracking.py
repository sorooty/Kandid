"""Applications after the watch: status changes, attached documents, follow-up and weekly review."""

from collections import Counter
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import Engine
from sqlmodel import Session, col, select

from kandid_tools.db import Application, Event, Offer, now, session
from kandid_tools.files import is_inside
from kandid_tools.status import Status, can_transition

# Days without news after which a sent application deserves a follow-up, then a second one.
FOLLOW_UP_DAYS = 7
# Statuses that mean the company answered.
ANSWERS = frozenset({Status.INTERVIEW, Status.OFFER, Status.REJECTED})
_CLOSED = frozenset({Status.ARCHIVED, Status.REJECTED})


class NotFound(ValueError):
    pass


class EventView(BaseModel):
    at: datetime
    kind: str
    detail: str


class OfferView(BaseModel):
    id: int
    status: Status
    source: str
    company: str
    title: str
    location: str | None
    contract: str | None
    url: str | None
    score: int
    justification: str
    points_to_check: list[str]
    description: str
    events: list[EventView]


class OfferRow(BaseModel):
    id: int
    score: int
    company: str
    title: str
    source: str
    url: str | None
    status: Status


class FollowUp(BaseModel):
    id: int
    company: str
    title: str
    status: Status
    days: int
    action: str


class Review(BaseModel):
    since: datetime
    found: int
    sent: int
    answered: int
    answer_rate: float | None
    by_status: dict[str, int]
    # Applications sent, and those that got an interview, per source of the offer.
    sent_by_source: dict[str, int]
    interviews_by_source: dict[str, int]


def _application(db: Session, offer_id: int) -> tuple[Application, int]:
    application = db.exec(select(Application).where(Application.offer_id == offer_id)).first()
    if application is None or application.id is None:
        raise NotFound(f"offre {offer_id} introuvable")
    return application, application.id


def change_status(engine: Engine, offer_id: int, target: Status, note: str = "") -> Status:
    """Move an application, logging the change (and the note, such as a discard reason)."""
    with session(engine) as db:
        application, application_id = _application(db, offer_id)
        current = application.status
        if not can_transition(current, target):
            raise ValueError(f"passage interdit : {current.label} vers {target.label}")
        application.status = target
        application.updated_at = now()
        db.add(Event(application_id=application_id, kind="status", detail=target.value))
        if note:
            db.add(Event(application_id=application_id, kind="note", detail=note))
        db.commit()
        return current


def attach_document(engine: Engine, offer_id: int, path: Path, roots: list[Path]) -> None:
    """Only files under `roots` (data and applications folders): a document event is later read
    back by skills, so it must not point them at an arbitrary file of the machine."""
    if not path.is_file():
        raise ValueError(f"fichier introuvable : {path}")
    if not any(is_inside(path, root) for root in roots):
        raise ValueError(f"fichier hors des dossiers Kandid : {path}")
    with session(engine) as db:
        _, application_id = _application(db, offer_id)
        db.add(Event(application_id=application_id, kind="document", detail=str(path.resolve())))
        db.commit()


def list_offers(
    engine: Engine, status: Status | None, limit: int, offset: int = 0
) -> list[OfferRow]:
    """Offers, best scored first; archived ones only when asked for."""
    query = (
        select(
            Offer.id,
            Offer.score,
            Offer.company,
            Offer.title,
            Offer.source,
            Offer.url,
            Application.status,
        )
        .join(Application, col(Application.offer_id) == col(Offer.id))
        .order_by(col(Offer.score).desc(), col(Offer.first_seen).desc())
        .limit(limit)
        .offset(offset)
    )
    if status is None:
        query = query.where(Application.status != Status.ARCHIVED)
    else:
        query = query.where(Application.status == status)
    with session(engine) as db:
        rows = db.exec(query).all()
    keys = OfferRow.model_fields.keys()
    return [OfferRow.model_validate(dict(zip(keys, row, strict=True))) for row in rows]


def offer_view(engine: Engine, offer_id: int) -> OfferView:
    with session(engine) as db:
        offer = db.get(Offer, offer_id)
        if offer is None or offer.id is None:
            raise NotFound(f"offre {offer_id} introuvable")
        application, application_id = _application(db, offer_id)
        events = db.exec(
            select(Event).where(Event.application_id == application_id).order_by(col(Event.at))
        ).all()
        return OfferView(
            id=offer.id,
            status=application.status,
            **offer.model_dump(
                include={
                    "source",
                    "company",
                    "title",
                    "location",
                    "contract",
                    "url",
                    "score",
                    "justification",
                    "points_to_check",
                    "description",
                }
            ),
            events=[EventView(at=e.at, kind=e.kind, detail=e.detail) for e in events],
        )


def _action(status: Status, days: int, offer_id: int) -> str:
    if status is Status.TO_REVIEW:
        return f"décider : /kandid:postuler {offer_id} ou kandid offre ecarter {offer_id}"
    if status is Status.TO_PREPARE:
        return f"préparer : /kandid:postuler {offer_id}"
    if status is Status.READY:
        return "envoyer la candidature (à faire par toi)"
    if status is Status.SENT:
        return "relancer (J+7) : /kandid:relance" if days >= FOLLOW_UP_DAYS else "attendre"
    if status is Status.FOLLOWED_UP:
        return "seconde relance (J+14) : /kandid:relance" if days >= FOLLOW_UP_DAYS else "attendre"
    if status is Status.INTERVIEW:
        return f"préparer l'entretien : /kandid:prep-entretien {offer_id}"
    return "répondre à l'offre"


def follow_up(engine: Engine, today: datetime) -> list[FollowUp]:
    """Open applications, the most urgent first: the longest without change."""
    query = (
        select(Offer.id, Offer.company, Offer.title, Application.status, Application.updated_at)
        .join(Application, col(Application.offer_id) == col(Offer.id))
        .where(col(Application.status).not_in(_CLOSED))
        .order_by(col(Application.updated_at))
    )
    with session(engine) as db:
        rows = db.exec(query).all()
    items: list[FollowUp] = []
    for offer_id, company, title, status, updated_at in rows:
        # SQLite returns naive datetimes: they were stored in UTC.
        days = (today - updated_at.replace(tzinfo=today.tzinfo)).days
        action = _action(status, days, offer_id)
        items.append(FollowUp(id=offer_id, company=company, title=title, status=status,
                              days=days, action=action))  # fmt: skip
    return items


def review(engine: Engine, since: datetime) -> Review:
    """What happened since `since`: offers found, applications sent and answered, per source."""
    with session(engine) as db:
        found = db.exec(
            select(Application.status).where(col(Application.created_at) >= since)
        ).all()
        moves = db.exec(
            select(Event.application_id, Event.detail, Offer.source)
            .join(Application, col(Application.id) == col(Event.application_id))
            .join(Offer, col(Offer.id) == col(Application.offer_id))
            .where(Event.kind == "status", col(Event.at) >= since)
        ).all()
    sent_ids = {app for app, detail, _ in moves if detail == Status.SENT}
    answered = {app for app, detail, _ in moves if app in sent_ids and detail in ANSWERS}
    sources = {app: source for app, _, source in moves}
    interviews = {app for app, detail, _ in moves if detail == Status.INTERVIEW}
    return Review(
        since=since,
        found=len(found),
        sent=len(sent_ids),
        answered=len(answered),
        answer_rate=round(len(answered) / len(sent_ids), 2) if sent_ids else None,
        by_status=dict(Counter(status.value for status in found)),
        sent_by_source=dict(Counter(sources[app] for app in sent_ids)),
        interviews_by_source=dict(Counter(sources[app] for app in interviews)),
    )
