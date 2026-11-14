"""Stand and gate → zone, and walking distance between zones (data/reference/hkg_zones.yaml).

The identifiers are REAL (HKIA); the zones and distances are ASSUMED and live in the YAML file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from flowcore.config import find_repo_root

_NUMBER = re.compile(r"^([A-Z]*)(\d+)")


@dataclass(frozen=True)
class Place:
    zone: str
    remote: bool      # remote stand: a bus ride before the walk starts
    known: bool       # False when the stand or gate was missing or not in the table


@dataclass(frozen=True)
class Zones:
    zones: dict
    ranges: tuple
    remote_arrival_zone: str
    same_zone_m: float
    transfer_detour_m: float
    default_zone: str

    def _zone_for_number(self, number: int) -> str | None:
        for low, high, zone in self.ranges:
            if low <= number <= high:
                return zone
        return None

    def stand(self, stand: str | None) -> Place:
        """Where an arriving passenger starts walking."""
        match = _NUMBER.match(stand or "")
        if not match:
            return Place(self.default_zone, False, False)
        number = int(match[2])
        zone = self._zone_for_number(number)
        if zone and zone != "bus_gates":
            return Place(zone, False, True)
        if number >= 100:  # three-digit stand outside the Midfield range
            return Place(self.remote_arrival_zone, True, True)
        return Place(self.default_zone, False, False)

    def gate(self, gate: str | None) -> Place:
        """Where a departing passenger has to be."""
        match = _NUMBER.match(gate or "")
        zone = self._zone_for_number(int(match[2])) if match else None
        return Place(zone or self.default_zone, False, zone is not None)

    def walk_m(self, start: str, end: str) -> float:
        if start == end:
            return float(self.same_zone_m)
        a, b = self.zones[start], self.zones[end]
        return float(abs(a["x"] - b["x"]) + a["branch"] + b["branch"] + self.transfer_detour_m)

    def train_minutes(self, start: str, end: str) -> float:
        """Train time when exactly one end is a zone reached by train (Midfield)."""
        a = self.zones[start].get("train_minutes", 0)
        b = self.zones[end].get("train_minutes", 0)
        return float(max(a, b)) if start != end else 0.0

    def name(self, zone: str) -> str:
        return self.zones[zone]["name"]


@lru_cache(maxsize=4)
def load_zones(path: str | None = None) -> Zones:
    file = Path(path) if path else find_repo_root() / "data" / "reference" / "hkg_zones.yaml"
    raw = yaml.safe_load(file.read_text(encoding="utf-8"))
    return Zones(
        zones=raw["zones"],
        ranges=tuple((item["from"], item["to"], item["zone"]) for item in raw["number_ranges"]),
        remote_arrival_zone=raw["remote_arrival_zone"],
        same_zone_m=raw["same_zone_m"],
        transfer_detour_m=raw["transfer_detour_m"],
        default_zone=raw["default_zone"],
    )
