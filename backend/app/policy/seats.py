"""Seat inventory on later flights, and the guard on the original seat (AGENTS.md §11.3, §2.1).

Free seats are ASSUMED (config/policy.yaml): OAG gives aircraft capacity, not availability.
"""

from __future__ import annotations

from datetime import datetime

# The only two reasons an original seat may ever be released (non-negotiable 1).
PASSENGER_CHOSE = "passenger_chose_alternative"
GATE_CLOSED = "gate_closed_not_boarded"
ALLOWED_RELEASE_REASONS = {PASSENGER_CHOSE, GATE_CLOSED}


class OriginalSeatError(RuntimeError):
    """Something tried to release an original seat early."""


def release_original_seat(party_state, reason: str, t: datetime, gate_close: datetime) -> None:
    """The single code path that releases an original seat. Everything else must call this."""
    if reason not in ALLOWED_RELEASE_REASONS:
        raise OriginalSeatError(f"Original seat may not be released for reason '{reason}'.")
    if reason == GATE_CLOSED and t < gate_close:
        raise OriginalSeatError("Original seat may not be released before gate close.")
    if reason == PASSENGER_CHOSE and not party_state.chosen_kind:
        raise OriginalSeatError("Original seat may not be released without the passenger's choice.")
    party_state.original_seat_held = False
    party_state.release_reason = reason


class Seats:
    """Free seats per (flight, cabin). Other passengers book over time, so the pool shrinks."""

    def __init__(self, policy: dict, start: datetime):
        self.initial = dict(policy["free_seats"])
        self.depletion_per_hour = float(policy["seat_depletion_per_hour"])
        self.start = start
        self.taken: dict[tuple[str, str], int] = {}

    def free(self, flight_key: str, cabin: str, t: datetime) -> int:
        hours = max((t - self.start).total_seconds() / 3600.0, 0.0)
        pool = max(self.initial.get(cabin, 0) - int(self.depletion_per_hour * hours), 0)
        return max(pool - self.taken.get((flight_key, cabin), 0), 0)

    def take(self, flight_key: str, cabin: str, seats: int, t: datetime) -> bool:
        """All seats or none: a party is never split (non-negotiable 4)."""
        if self.free(flight_key, cabin, t) < seats:
            return False
        self.taken[(flight_key, cabin)] = self.taken.get((flight_key, cabin), 0) + seats
        return True

    def give_back(self, flight_key: str, cabin: str, seats: int) -> None:
        self.taken[(flight_key, cabin)] = max(self.taken.get((flight_key, cabin), 0) - seats, 0)

    def held_total(self) -> int:
        return sum(self.taken.values())
