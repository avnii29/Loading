from app.models.enums import DonationStatus

ALLOWED_TRANSITIONS: dict[DonationStatus, set[DonationStatus]] = {
    DonationStatus.DRAFT: {DonationStatus.SUBMITTED, DonationStatus.CANCELLED},
    DonationStatus.SUBMITTED: {DonationStatus.ASSESSING, DonationStatus.CANCELLED},
    DonationStatus.ASSESSING: {
        DonationStatus.MATCHING,
        DonationStatus.MATCHED,
        DonationStatus.ASSIGNED,
        DonationStatus.UNDER_REVIEW,
        DonationStatus.REJECTED,
        DonationStatus.RECOVERY_PENDING,
        DonationStatus.CANCELLED,
    },
    DonationStatus.MATCHING: {
        DonationStatus.MATCHED,
        DonationStatus.ASSIGNED,
        DonationStatus.EXPIRED,
        DonationStatus.CANCELLED,
    },
    DonationStatus.MATCHED: {DonationStatus.ASSIGNED, DonationStatus.CANCELLED},
    DonationStatus.ASSIGNED: {
        DonationStatus.PICKUP_PENDING,
        DonationStatus.IN_TRANSIT,
        DonationStatus.CANCELLED,
    },
    DonationStatus.PICKUP_PENDING: {DonationStatus.IN_TRANSIT, DonationStatus.CANCELLED},
    DonationStatus.IN_TRANSIT: {
        DonationStatus.DELIVERED,
        DonationStatus.UNDER_REVIEW,
        DonationStatus.REJECTED,
        DonationStatus.CANCELLED,
    },
    DonationStatus.DELIVERED: {DonationStatus.UNDER_REVIEW},
    DonationStatus.UNDER_REVIEW: {DonationStatus.ACCEPTED, DonationStatus.REJECTED},
    DonationStatus.ACCEPTED: {DonationStatus.COMPLETED},
    DonationStatus.REJECTED: {DonationStatus.RECOVERY_PENDING, DonationStatus.CANCELLED},
    DonationStatus.RECOVERY_PENDING: {
        DonationStatus.RECOVERY_ASSIGNED,
        DonationStatus.CANCELLED,
        DonationStatus.EXPIRED,
    },
    DonationStatus.RECOVERY_ASSIGNED: {DonationStatus.RECOVERED, DonationStatus.CANCELLED},
    DonationStatus.RECOVERED: {DonationStatus.COMPLETED},
    DonationStatus.COMPLETED: set(),
    DonationStatus.CANCELLED: set(),
    DonationStatus.EXPIRED: set(),
}

DONOR_CANCELABLE = {
    DonationStatus.DRAFT,
    DonationStatus.SUBMITTED,
    DonationStatus.ASSESSING,
    DonationStatus.MATCHING,
}

STATUS_LABELS = {
    DonationStatus.DRAFT: "Draft",
    DonationStatus.SUBMITTED: "Submitted",
    DonationStatus.ASSESSING: "Finding the right route…",
    DonationStatus.MATCHING: "Finding the right route…",
    DonationStatus.MATCHED: "A destination is ready",
    DonationStatus.ASSIGNED: "Someone is assigned",
    DonationStatus.PICKUP_PENDING: "Pickup pending",
    DonationStatus.IN_TRANSIT: "On the way",
    DonationStatus.DELIVERED: "Delivered",
    DonationStatus.UNDER_REVIEW: "Being reviewed",
    DonationStatus.ACCEPTED: "Accepted",
    DonationStatus.REJECTED: "Not accepted",
    DonationStatus.RECOVERY_PENDING: "Recovery being considered",
    DonationStatus.RECOVERY_ASSIGNED: "Recovery assigned",
    DonationStatus.RECOVERED: "Recovered",
    DonationStatus.COMPLETED: "Completed",
    DonationStatus.CANCELLED: "Cancelled",
    DonationStatus.EXPIRED: "Expired",
}


def can_transition(current: DonationStatus, target: DonationStatus) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())


def assert_transition(current: DonationStatus, target: DonationStatus) -> None:
    if current == target:
        raise ValueError("Donation is already in that state.")
    if not can_transition(current, target):
        raise ValueError(
            f"Cannot move a donation from {current.value} to {target.value}."
        )
