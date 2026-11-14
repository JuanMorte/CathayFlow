from pathlib import Path

import pytest

from flowcore.engine.zones import load_zones

ZONES_FILE = str(Path(__file__).resolve().parents[2] / "data" / "reference" / "hkg_zones.yaml")


@pytest.fixture(scope="module")
def zones():
    return load_zones(ZONES_FILE)


@pytest.mark.parametrize("stand, zone, remote", [
    ("S1", "east", False), ("N5", "central", False), ("R17", "satellite", False),
    ("S23", "mid", False), ("W48", "west", False), ("N64", "northwest", False),
    ("W61", "northwest", False), ("D210", "midfield", False),
    ("S108", "east", True), ("N141", "east", True), ("W121L", "east", True), ("D319", "east", True),
])
def test_stands(zones, stand, zone, remote):
    place = zones.stand(stand)
    assert (place.zone, place.remote, place.known) == (zone, remote, True)


@pytest.mark.parametrize("gate, zone", [
    ("2", "east"), ("9", "central"), ("17", "satellite"), ("30", "mid"), ("41", "west"),
    ("67", "northwest"), ("210", "midfield"), ("515", "bus_gates"),
])
def test_gates(zones, gate, zone):
    place = zones.gate(gate)
    assert (place.zone, place.remote, place.known) == (zone, False, True)


def test_missing_or_unknown_falls_back_and_says_so(zones):
    for value in (None, "", "X", "55"):
        assert zones.stand(value) == zones.gate(value)
        assert zones.gate(value).zone == "central" and zones.gate(value).known is False


def test_walk_distances_by_hand(zones):
    assert zones.walk_m("west", "west") == 120
    # east (x 100) → northwest (x 850, branch 300): 750 + 300 + 150 detour
    assert zones.walk_m("east", "northwest") == 1200
    # satellite (x 350, branch 500) → mid (x 600): 250 + 500 + 150
    assert zones.walk_m("satellite", "mid") == 900
    assert zones.walk_m("mid", "satellite") == zones.walk_m("satellite", "mid")


def test_train_only_for_midfield(zones):
    assert zones.train_minutes("west", "midfield") == 6
    assert zones.train_minutes("midfield", "midfield") == 0
    assert zones.train_minutes("east", "west") == 0


def test_every_cathay_stand_and_gate_in_the_data_is_known(zones):
    """Identifiers seen on Cathay-operated flights, 2026-08-15 to 2026-11-13 (HKIA)."""
    stands = ("N5 N10 N12 N24 N36 N60 N70 N141 N145 R13 R21 S1 S4 S11 S23 S49 S101 S111 "
              "W40 W50 W61 W71 W121L W125").split()
    gates = "1 12 13 21 23 36 40 50 60 71 511 524".split()
    assert all(zones.stand(stand).known for stand in stands)
    assert all(zones.gate(gate).known for gate in gates)
