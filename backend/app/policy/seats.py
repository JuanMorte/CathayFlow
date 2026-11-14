"""Seat inventory on later flights, and the guard on the original seat (AGENTS.md §11.3, §2.1).

Free seats on a flight = its seats per cabin (aircraft type REAL from OAG, layout ASSUMED) x
(1 - Cathay's published passenger load factor, REAL). A load factor is how full flights are on
average at departure, so this is the number of seats left unsold, not a guess per flight.
Flights with no known type fall back to config/policy.yaml `free_seats` (ASSUMED).
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
    """Free seats per (flight, cabin), less those already held or booked for our passengers."""

    def __init__(self, policy: dict, flights: dict | None = None, load_factor: float | None = None):
        self.fallback = dict(policy["free_seats"])
        self.flights = flights or {}
        self.load_factor = load_factor
        self.taken: dict[tuple[str, str], int] = {}

    def capacity(self, flight_key: str, cabin: str) -> int:
        layout = (self.flights.get(flight_key) or {}).get("cabin_seats")
        if layout and self.load_factor is not None:
            return int(layout.get(cabin, 0) * (1.0 - self.load_factor))
        return int(self.fallback.get(cabin, 0))

    def free(self, flight_key: str, cabin: str, t: datetime | None = None) -> int:
        return max(self.capacity(flight_key, cabin) - self.taken.get((flight_key, cabin), 0), 0)

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
