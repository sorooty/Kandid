"""Recruiter mails, read by the skill through the user's mail connector, turned into suggestions.

Nothing here reads a mailbox or changes a status: the skill brings the mails, the user accepts each
suggestion.
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel
from sqlalchemy import Engine
from sqlmodel import col, select

from kandid_tools.ats import norm
from kandid_tools.config import MailConfig
from kandid_tools.db import Application, Offer, session
from kandid_tools.dedup import fingerprint
from kandid_tools.status import Status, can_transition


class Mail(BaseModel):
    """Only what classification needs: no body, so a mail never brings a CV or letter along."""

    source: str
    id: str
    sender: str = ""
    subject: str = ""
    preview: str = ""
    date: datetime | None = None
    url: str | None = None


class Kind(StrEnum):
    REJECTION = "rejection"
    INTERVIEW = "interview"
    ACKNOWLEDGEMENT = "acknowledgement"
    OTHER = "other"


class Suggestion(BaseModel):
    mail: Mail
    kind: Kind
    offer_id: int | None = None
    company: str | None = None
    current: Status | None = None
    # None when the mail changes nothing (already up to date, or a move the statuses forbid).
    target: Status | None = None


class Analysis(BaseModel):
    suggestions: list[Suggestion]
    ignored: int


_TARGETS = {
    Kind.REJECTION: Status.REJECTED,
    Kind.INTERVIEW: Status.INTERVIEW,
    Kind.ACKNOWLEDGEMENT: Status.SENT,
}


def _has(text: str, patterns: list[str]) -> bool:
    return any(norm(pattern) in text for pattern in patterns)


def is_noise(mail: Mail, config: MailConfig) -> bool:
    return _has(norm(mail.sender), config.ignore_senders) or _has(
        norm(mail.subject), config.ignore_subjects
    )


def classify(mail: Mail, config: MailConfig) -> Kind:
    # Refusals thank the candidate and often recall the interview: they are tested first.
    text = norm(f"{mail.subject} {mail.preview}")
    for kind, patterns in (
        (Kind.REJECTION, config.rejection),
        (Kind.INTERVIEW, config.interview),
        (Kind.ACKNOWLEDGEMENT, config.acknowledgement),
    ):
        if _has(text, patterns):
            return kind
    return Kind.OTHER


def company_key(company: str) -> str:
    return fingerprint(company, "").split("|")[0]


Known = tuple[str, int, Status, str, datetime]


def _match(mail: Mail, companies: list[Known]) -> Known | None:
    """`companies` is sorted longest key first, so "Valeo Brain" wins over "Valeo"."""
    text = f" {company_key(f'{mail.sender} {mail.subject} {mail.preview}')} "
    return next((row for row in companies if f" {row[0]} " in text), None)


def _naive_utc(moment: datetime) -> datetime:
    # SQLite gives back naive datetimes, stored in UTC.
    return moment.astimezone(UTC).replace(tzinfo=None) if moment.tzinfo else moment


def suggest(engine: Engine, mails: list[Mail], config: MailConfig) -> Analysis:
    with session(engine) as db:
        rows = db.exec(
            select(Offer.id, Offer.company, Application.status, Application.updated_at).join(
                Application, col(Application.offer_id) == col(Offer.id)
            )
        ).all()
    companies = sorted(
        ((company_key(company), offer_id, status, company, changed)
         for offer_id, company, status, changed in rows if len(company_key(company)) >= 3),
        key=lambda row: len(row[0]),
        reverse=True,
    )  # fmt: skip
    kept = [mail for mail in mails if not is_noise(mail, config)]
    suggestions: list[Suggestion] = []
    for mail in kept:
        kind = classify(mail, config)
        found = _match(mail, companies)
        if found is None:
            suggestions.append(Suggestion(mail=mail, kind=kind))
            continue
        _, offer_id, current, company, changed = found
        wanted = _TARGETS.get(kind)
        # A mail older than the last change is already taken into account (or overtaken).
        stale = mail.date is not None and _naive_utc(mail.date) <= _naive_utc(changed)
        allowed = wanted is not None and can_transition(current, wanted)
        target = wanted if allowed and not stale else None
        suggestions.append(
            Suggestion(mail=mail, kind=kind, offer_id=offer_id, company=company,
                       current=current, target=target)
        )  # fmt: skip
    suggestions.sort(key=lambda s: s.mail.date.timestamp() if s.mail.date else 0.0, reverse=True)
    return Analysis(suggestions=suggestions, ignored=len(mails) - len(kept))
