import pytest

from app.models.enums import DonationStatus
from app.services.status import assert_transition, can_transition


def test_submitted_to_assessing_is_allowed():
    assert can_transition(DonationStatus.SUBMITTED, DonationStatus.ASSESSING)


def test_invalid_transition_is_rejected():
    with pytest.raises(ValueError):
        assert_transition(DonationStatus.SUBMITTED, DonationStatus.COMPLETED)


def test_rejected_does_not_auto_recover():
    assert not can_transition(DonationStatus.REJECTED, DonationStatus.RECOVERED)
    assert can_transition(DonationStatus.REJECTED, DonationStatus.RECOVERY_PENDING)


def test_terminal_states_have_no_exits():
    assert not can_transition(DonationStatus.COMPLETED, DonationStatus.SUBMITTED)
    assert not can_transition(DonationStatus.CANCELLED, DonationStatus.ASSESSING)
    assert not can_transition(DonationStatus.EXPIRED, DonationStatus.MATCHING)
