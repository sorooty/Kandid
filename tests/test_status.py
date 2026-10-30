import pytest

from kandid_tools.status import Status, allowed_transitions, can_transition


def test_preparation_flow():
    assert can_transition(Status.TO_REVIEW, Status.TO_PREPARE)
    assert can_transition(Status.TO_PREPARE, Status.READY)
    assert can_transition(Status.READY, Status.SENT)
    assert can_transition(Status.READY, Status.TO_PREPARE)


def test_normal_flow_after_sending():
    assert can_transition(Status.SENT, Status.INTERVIEW)
    assert can_transition(Status.INTERVIEW, Status.OFFER)


def test_cannot_skip_preparation_or_sending():
    assert not can_transition(Status.TO_REVIEW, Status.SENT)
    assert not can_transition(Status.TO_PREPARE, Status.INTERVIEW)
    assert not can_transition(Status.READY, Status.INTERVIEW)


def test_reopen_after_refusal_or_follow_up():
    assert can_transition(Status.FOLLOWED_UP, Status.INTERVIEW)
    assert can_transition(Status.REJECTED, Status.OFFER)


def test_several_interview_rounds():
    assert can_transition(Status.INTERVIEW, Status.INTERVIEW)


@pytest.mark.parametrize("status", [s for s in Status if s is not Status.ARCHIVED])
def test_every_column_can_be_archived(status):
    assert can_transition(status, Status.ARCHIVED)


def test_archiving_is_final():
    assert allowed_transitions(Status.ARCHIVED) == frozenset()


def test_every_status_has_a_french_label():
    assert Status.READY.label == "Prêt"
    assert all(s.label for s in Status)
