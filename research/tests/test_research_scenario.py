"""The scenario's passenger counts follow the published-figures formula, flight by flight.

    connecting passengers off an arrival = seats x Cathay load factor x HKG transfer share
"""

from pathlib import Path

import pytest
import yaml

from flowcore.scenario import load_scenario, scenarios_dir

SCENARIO = "2026-10-22-evening"
ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(not (scenarios_dir() / SCENARIO).is_dir(), reason="scenario not built")


@pytest.fixture(scope="module")
def scenario():
    return load_scenario(SCENARIO)


@pytest.fixture(scope="module")
def seat_table():
    return yaml.safe_load((ROOT / "data" / "reference" / "aircraft_seats.yaml").read_text())


def test_published_inputs_are_recorded_with_sources(scenario):
    meta = scenario["meta"]
    assert meta["load_factor"] == 0.872 and meta["transfer_share"] == 0.28
    assert meta["labels"]["load_factor"] == "REAL" and meta["labels"]["transfer_share"] == "REAL"
    assert "Cathay" in meta["sources"]["load_factor"] and "AAHK" in meta["sources"]["transfer_share"]


def test_every_arrival_has_a_real_aircraft_type(scenario, seat_table):
    arrivals = [f for f in scenario["flights"].values() if f["kind"] == "arr" and not f["cancelled"]]
    assert arrivals
    for flight in arrivals:
        assert flight["aircraft_type"] in seat_table["types"], flight["flight"]


def test_connecting_passengers_follow_the_formula(scenario):
    meta, flights = scenario["meta"], scenario["flights"]
    on_board = {}
    for party in scenario["parties"]:
        if party["party_id"] != "MEI":
            on_board[party["inbound"]] = on_board.get(party["inbound"], 0) + party["size"]
    for row in meta["connections_per_arrival"]:
        expected = round(row["seats"] * meta["load_factor"] * meta["transfer_share"])
        key = next(f["key"] for f in flights.values() if f["kind"] == "arr" and f["flight"] == row["flight"])
        if row["onward_flights"]:
            assert row["connecting"] == expected == on_board.get(key, 0), row["flight"]
        else:
            assert row["connecting"] == 0      # nowhere plausible to go within four hours


def test_cabins_follow_the_aircraft(scenario):
    """Nobody connects off an aircraft in a cabin it does not have (an A321neo has no Premium Economy)."""
    flights = scenario["flights"]
    for party in scenario["parties"]:
        layout = flights[party["inbound"]]["cabin_seats"]
        assert layout[party["cabin"]] > 0, (party["party_id"], party["cabin"])


def test_connections_are_plausible(scenario):
    flights = scenario["flights"]
    for party in scenario["parties"]:
        inbound, outbound = flights[party["inbound"]], flights[party["outbound"]]
        assert 50 <= party["sched_gap_min"] <= 240
        assert inbound["airport"] != outbound["airport"]
        assert party["is_synthetic"] is True
