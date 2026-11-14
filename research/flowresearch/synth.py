"""Synthetic connections and passengers (AGENTS.md §7.5). Always labelled SYNTHETIC.

No real passenger data is used anywhere. Everything here is generated from a seed, so the same
seed and the same flights give the same people.
"""

from __future__ import annotations

import numpy as np

# ASSUMED (AGENTS.md §7.5): mean passengers per connecting flight pair.
MEAN_PAX_PER_PAIR = 2.21
# ASSUMED: how common each scheduled gap is among people who book a connection.
GAP_WEIGHTS = [(50, 89, 0.45), (90, 180, 1.0), (181, 240, 0.6)]
# ASSUMED mixes.
CABIN_MIX = {"J": 0.14, "W": 0.08, "Y": 0.78}
PARTY_SIZE_MIX = {1: 0.70, 2: 0.22, 3: 0.05, 4: 0.03}
TIER_MIX = {"Diamond": 0.04, "Gold": 0.10, "Silver": 0.16, "Green": 0.30, "None": 0.40}
ASSISTANCE_SHARE = 0.03
PREFERENCE_MIX = {"earliest_arrival": 0.45, "keep_cabin": 0.25, "rest_first": 0.10, "unset": 0.20}
# ASSUMED seat rows per cabin, for a plausible seat number and the deplaning position.
CABIN_ROWS = {"J": (11, 26), "W": (30, 36), "Y": (39, 72)}
SEAT_LETTERS = {"J": "ADGK", "W": "ACDEGHK", "Y": "ABCDEGHJK"}

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


def make_party(rng: np.random.Generator, party_id: str, size: int | None = None,
               cabin: str | None = None) -> dict:
    size = size or int(_pick(rng, PARTY_SIZE_MIX))
    cabin = cabin or _pick(rng, CABIN_MIX)
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


def make_connections(inbounds: list[dict], outbounds: list[dict], airports: dict,
                     implausible: list, seed: int) -> list[dict]:
    """Parties per plausible inbound → outbound pair with a 50 to 240 minute scheduled gap."""
    rng = np.random.default_rng(seed)
    parties = []
    for inbound in sorted(inbounds, key=lambda f: (f["sched"], f["flight"])):
        for outbound in sorted(outbounds, key=lambda f: (f["sched"], f["flight"])):
            gap = (outbound["sched"] - inbound["sched"]).total_seconds() / 60
            weight = gap_weight(gap)
            if not weight or not plausible(inbound["airport"], outbound["airport"], airports, implausible):
                continue
            passengers = int(rng.poisson(MEAN_PAX_PER_PAIR * weight))
            while passengers > 0:
                party = make_party(rng, f"P{len(parties) + 1:04d}")
                party["size"] = min(party["size"], passengers)
                party["members"] = party["members"][:party["size"]]
                party.update(inbound=inbound["key"], outbound=outbound["key"],
                             sched_gap_min=int(gap))
                parties.append(party)
                passengers -= party["size"]
    return parties
