"""Application statuses (the Kanban columns) and the moves allowed between them."""

from enum import StrEnum


class Status(StrEnum):
    TO_REVIEW = "to_review"
    TO_PREPARE = "to_prepare"
    READY = "ready"
    SENT = "sent"
    FOLLOWED_UP = "followed_up"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    ARCHIVED = "archived"

    @property
    def label(self) -> str:
        return LABELS[self]


LABELS = {
    Status.TO_REVIEW: "À voir",
    Status.TO_PREPARE: "À préparer",
    Status.READY: "Prêt",
    Status.SENT: "Envoyée",
    Status.FOLLOWED_UP: "Relance",
    Status.INTERVIEW: "Entretien",
    Status.OFFER: "Offre",
    Status.REJECTED: "Refus",
    Status.ARCHIVED: "Archivée",
}

# Rejection is not final: recruiters often come back after a "no". A silence needs no status
# of its own, it shows in the dates. Every column can be archived; archiving is final.
_TRANSITIONS: dict[Status, frozenset[Status]] = {
    Status.TO_REVIEW: frozenset({Status.TO_PREPARE}),
    Status.TO_PREPARE: frozenset({Status.READY}),
    Status.READY: frozenset({Status.SENT, Status.TO_PREPARE}),
    Status.SENT: frozenset({Status.FOLLOWED_UP, Status.INTERVIEW, Status.OFFER, Status.REJECTED}),
    Status.FOLLOWED_UP: frozenset({Status.INTERVIEW, Status.OFFER, Status.REJECTED}),
    Status.INTERVIEW: frozenset({Status.INTERVIEW, Status.OFFER, Status.REJECTED}),
    Status.OFFER: frozenset({Status.REJECTED}),
    Status.REJECTED: frozenset({Status.INTERVIEW, Status.OFFER}),
    Status.ARCHIVED: frozenset(),
}


def allowed_transitions(current: Status) -> frozenset[Status]:
    if current is Status.ARCHIVED:
        return _TRANSITIONS[current]
    return _TRANSITIONS[current] | {Status.ARCHIVED}


def can_transition(current: Status, target: Status) -> bool:
    return target in allowed_transitions(current)
