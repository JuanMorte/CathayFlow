"""The Gate Planner on cases worked out by hand (spreads set to zero)."""

import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from flowcore.engine.gate_planner import PlanRequest, Road, airport_express, gate_at, plan
from flowcore.engine.time_to_gate import load_config
from flowcore.engine.zones import load_zones

ROOT = Path(__file__).resolve().parents[2]
HKT = timezone(timedelta(hours=8))


def at(hour, minute=0):
    return datetime(2026, 10, 22, hour, minute, tzinfo=HKT)


@pytest.fixture(scope="module")
def zones():
    return load_zones(str(ROOT / "data" / "reference" / "hkg_zones.yaml"))


@pytest.fixture
def config():
    flat = copy.deepcopy(load_config(str(ROOT / "config" / "engine.yaml")))
    flat["samples"] = 200
    planner = flat["planner"]
    for name in ("security_resident", "security_visitor"):
        planner[name]["sd"] = 0
    for name in ("peak", "offpeak"):
        planner["checkin_queue"][name]["sd"] = 0
    planner["airport_express"]["to_station"]["sd"] = 0
    flat["walk_speed"]["sd"] = 0
    return flat


def flight(**extra):
    base = {"key": "CX135@x", "kind": "dep", "flight": "CX135", "airport": "MEL", "city": "Melbourne",
            "sched": at(19), "actual": at(19), "cancelled": False, "gate": "49", "timeline": []}
    return {**base, **extra}


def fixed_road(minutes):
    return lambda when: Road(minutes, minutes, "google", "test", "REAL")


def test_hand_computed_plan(config, zones):
    # 19:00 departure, one bag → bag drop closes 18:00.
    # Check-in in the evening peak 20, e-Channel 5, walk central → gate 49 (west): 500 + 150 = 650 m
    # at 1.2 m/s = 9.03 min, road 30 (± 1 min floor spread) → about 64 min at the 85th percentile;
    # 18:00 − about 65 = about 16:55, rounded down to five minutes: 16:50 or 16:55 (sampling).
    result = plan(PlanRequest("central", "CX135@x"), flight(), at(15), config, zones, fixed_road(30), seed=1)
    assert result.deadline == at(18) and result.deadline_kind == "Bag drop closes"
    assert result.gate == "49"
    steps = {s["key"]: s for s in result.steps}
    assert steps["checkin"]["typical"] == 20 and steps["security"]["typical"] == 5 and steps["walk"]["typical"] == 9
    assert at(16, 50) <= result.leave_by <= at(16, 55)
    assert result.percentile == 85


def test_online_without_bags_skips_the_counter(config, zones):
    request = PlanRequest("central", "CX135@x", bags=0, checked_in_online=True)
    result = plan(request, flight(), at(15), config, zones, fixed_road(30), seed=1)
    assert result.deadline == at(18, 45) and result.deadline_kind == "Gate closes"
    assert {s["key"]: s for s in result.steps}["checkin"]["typical"] == 0
    assert not any("online" in n for n in result.nudges)


def test_visitor_and_relaxed_leave_earlier(config, zones):
    base = plan(PlanRequest("central", "CX135@x"), flight(), at(15), config, zones, fixed_road(30), seed=1)
    visitor = plan(PlanRequest("central", "CX135@x", hk_resident=False, buffer="relaxed"), flight(), at(15),
                   config, zones, fixed_road(30), seed=1)
    assert visitor.leave_by < base.leave_by


def test_gate_counts_only_once_published(config, zones):
    published = flight(gate="49", timeline=[{"at": at(15, 15), "state": "Scheduled", "est": at(19), "on_ground": None, "gate": "49"}])
    assert gate_at(published, at(15)) is None and gate_at(published, at(15, 15)) == "49"
    before = plan(PlanRequest("central", "CX135@x"), published, at(15), config, zones, fixed_road(30), seed=1)
    after = plan(PlanRequest("central", "CX135@x"), published, at(15, 20), config, zones, fixed_road(30), seed=1)
    # Until published, plan for a far gate (north-west: 950 m); gate 49 is nearer (650 m): never later.
    assert {s["key"]: s for s in before.steps}["walk"]["typical"] == 13
    assert after.leave_by >= before.leave_by


def test_a_published_delay_moves_the_plan(config, zones):
    delayed = flight(timeline=[
        {"at": at(15), "state": "Scheduled", "est": at(19), "on_ground": None, "gate": "49"},
        {"at": at(16), "state": "Scheduled", "est": at(19, 40), "on_ground": None, "gate": "49"},
    ])
    before = plan(PlanRequest("central", "CX135@x"), delayed, at(15, 30), config, zones, fixed_road(30), seed=1)
    after = plan(PlanRequest("central", "CX135@x"), delayed, at(16, 5), config, zones, fixed_road(30), seed=1)
    assert after.departure == at(19, 40) and after.leave_by == before.leave_by + timedelta(minutes=40)
    assert any("now leaves at 19:40" in n for n in after.nudges)


def test_airport_express_timetable(config):
    road = airport_express(config)
    # 15 to the station + half a 10-minute headway + 24 ride = 44 typical.
    assert road.typical == 44 and road.source == "airport_express" and road.label == "ASSUMED"
