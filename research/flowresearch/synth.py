"""Synthetic connections and passengers (AGENTS.md §7.5). Always labelled SYNTHETIC.

No real passenger data is used anywhere. Everything here is generated from a seed, so the same
seed and the same flights give the same people.

How many people connect off each arrival is not random noise: it is built from published figures
(see `transfer_count`), so the proportions on every flight can be argued for:

    connecting passengers = seats on that aircraft (REAL type, ASSUMED layout)
                          × Cathay passenger load factor (REAL, published monthly)
                          × Hong Kong transfer share (REAL, derived from AAHK figures)

Who those people are (names, tiers, groups, preferences) is SYNTHETIC.
"""

from __future__ import annotations

import numpy as np

# ASSUMED: how a connecting passenger's onward flight is spread over the gap after landing.
# Tight connections are booked less often than comfortable ones.
GAP_WEIGHTS = [(50, 89, 0.45), (90, 180, 1.0), (181, 240, 0.6)]
# ASSUMED mixes.
PARTY_SIZE_MIX = {1: 0.70, 2: 0.22, 3: 0.05, 4: 0.03}
TIER_MIX = {"Diamond": 0.04, "Gold": 0.10, "Silver": 0.16, "Green": 0.30, "None": 0.40}
ASSISTANCE_SHARE = 0.03
PREFERENCE_MIX = {"earliest_arrival": 0.45, "keep_cabin": 0.25, "rest_first": 0.10, "unset": 0.20}
# ASSUMED seat rows per cabin, for a plausible seat number and the deplaning position.
CABIN_ROWS = {"F": (1, 2), "J": (11, 26), "W": (30, 36), "Y": (39, 72)}
SEAT_LETTERS = {"F": "AK", "J": "ADGK", "W": "ACDEGHK", "Y": "ABCDEGHJK"}
CABINS = ("F", "J", "W", "Y")

GIVEN = ["Mei", "Aarav", "Hannah", "Kenji", "Sofia", "Wei", "Priya", "Lucas", "Yuna", "Daniel",
         "Amelia", "Hiro", "Ines", "Tariq", "Chloe", "Minh", "Olivia", "Rahul", "Sana", "Noah",
         "Siti", "Jun", "Elena", "Marcus", "Aiko", "Farah", "Leo", "Nadia", "Tom", "Grace"]
FAMILY = ["Chen", "Sharma", "Mueller", "Tanaka", "Rossi", "Wong", "Iyer", "Martin", "Kim", "Lee",
          "Clarke", "Sato", "Garcia", "Rahman", "Dubois", "Nguyen", "Brown", "Mehta", "Khan",
          "Wilson", "Lim", "Park", "Petrova", "Johnson", "Yamada", "Aziz", "Silva", "Haddad",
          "Evans", "Tan"]


def _pick(rng: np.random.Generator, mix: dict):
    keys = list(mix)
    return keys[int(rng.choice(len(keys), p=np.array(list(mix.values())) / sum(mix.values())))]


def gap_weight(gap_minutes: float) -> float:
    for low, high, weight in GAP_WEIGHTS:
        if low <= gap_minutes <= high:
            return weight
    return 0.0


def plausible(origin: str, destination: str, airports: dict, implausible: list) -> bool:
    if origin == destination or origin not in airports or destination not in airports:
        return False
    a, b = airports[origin]["region"], airports[destination]["region"]
    if a == b:
        return False
    return [a, b] not in implausible and [b, a] not in implausible


def seat_for(rng: np.random.Generator, cabin: str) -> tuple[str, float]:
    """A seat like 17A and its position in the cabin (0 = front row, 1 = back)."""
    first, last = CABIN_ROWS[cabin]
    row = int(rng.integers(first, last + 1))
    letter = SEAT_LETTERS[cabin][int(rng.integers(len(SEAT_LETTERS[cabin])))]
    return f"{row}{letter}", (row - first) / max(last - first, 1)


def make_party(rng: np.random.Generator, party_id: str, cabin: str, size: int | None = None) -> dict:
    size = size or int(_pick(rng, PARTY_SIZE_MIX))
    family = FAMILY[int(rng.integers(len(FAMILY)))]
    seat, row_frac = seat_for(rng, cabin)
    members = []
    for index in range(size):
        given = GIVEN[int(rng.integers(len(GIVEN)))]
        members.append({"pid": f"{party_id}-{index + 1}", "name": f"{given} {family}"})
    return {
        "party_id": party_id,
        "size": size,
        "cabin": cabin,
        "seat": seat,
        "row_frac": round(row_frac, 3),
        "tier": _pick(rng, TIER_MIX),
        "assistance": bool(rng.random() < ASSISTANCE_SHARE),
        "preference": _pick(rng, PREFERENCE_MIX),
        "members": members,
        "is_synthetic": True,
    }


def cabin_layout(flight: dict, seat_table: dict) -> dict:
    """Seats per cabin for this flight's aircraft (type REAL from OAG, layout ASSUMED)."""
    types = seat_table["types"]
    kind = flight.get("aircraft_type")
    layout = types.get(kind) or types[seat_table["default_type"]]
    return {cabin: int(layout.get(cabin, 0)) for cabin in CABINS}


def transfer_count(flight: dict, seat_table: dict, load_factor: float, transfer_share: float) -> int:
    """Connecting passengers off one arrival: seats x load factor x transfer share."""
    return int(round(sum(cabin_layout(flight, seat_table).values()) * load_factor * transfer_share))


def make_connections(inbounds: list[dict], outbounds: list[dict], airports: dict, implausible: list,
                     seat_table: dict, load_factor: float, transfer_share: float,
                     seed: int) -> tuple[list[dict], list[dict]]:
    """Parties connecting off each arrival onto later Cathay departures (50 to 240 min later).

    Returns the parties and one summary row per arrival (for the scenario README and tests).
    A party's cabin follows the arrival's real cabin split; its onward flight is drawn among the
    plausible departures, weighted by the gap.
    """
    rng = np.random.default_rng(seed)
    parties, summary = [], []
    for inbound in sorted(inbounds, key=lambda f: (f["sched"], f["flight"])):
        layout = cabin_layout(inbound, seat_table)
        target = transfer_count(inbound, seat_table, load_factor, transfer_share)
        choices, weights = [], []
        for outbound in sorted(outbounds, key=lambda f: (f["sched"], f["flight"])):
            gap = (outbound["sched"] - inbound["sched"]).total_seconds() / 60
            weight = gap_weight(gap)
            if weight and plausible(inbound["airport"], outbound["airport"], airports, implausible):
                choices.append((outbound, int(gap)))
                weights.append(weight)
        placed = 0
        if choices:
            probabilities = np.array(weights) / sum(weights)
            cabin_mix = {cabin: count for cabin, count in layout.items() if count}
            while placed < target:
                party = make_party(rng, f"P{len(parties) + 1:04d}", _pick(rng, cabin_mix))
                party["size"] = min(party["size"], target - placed)
                party["members"] = party["members"][:party["size"]]
                outbound, gap = choices[int(rng.choice(len(choices), p=probabilities))]
                party.update(inbound=inbound["key"], outbound=outbound["key"], sched_gap_min=gap)
                parties.append(party)
                placed += party["size"]
        summary.append({"flight": inbound["flight"], "from": inbound["airport"],
                        "aircraft_type": inbound.get("aircraft_type"), "seats": sum(layout.values()),
                        "connecting": placed, "onward_flights": len(choices)})
    return parties, summary
