"""Gate Planner endpoints: choices, a plan, the timetable fallback, and refusals."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import planner
from app.main import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("OFFLINE", "1")     # no cache in tests: every road lookup falls back
    monkeypatch.setenv("FLOW_TICK_SECONDS", "0.05")
    with TestClient(create_app()) as test_client:
        test_client.post("/api/replay/control", json={"action": "seek", "t": "2026-10-22T15:00:00+08:00"})
        yield test_client


def test_options_list_later_departures(client):
    body = client.get("/api/planner/options").json()
    assert {o["id"] for o in body["origins"]} >= {"central", "tst"}
    assert body["flights"] and all(f["sched"] >= "2026-10-22T16:00:00+08:00" for f in body["flights"])
    cx135 = next(f for f in body["flights"] if f["flight"] == "CX135")
    assert cx135["gate"] is None            # published at 15:15, not yet known at 15:00


def test_plan_offline_uses_the_timetable(client):
    key = next(f["key"] for f in client.get("/api/planner/options").json()["flights"] if f["flight"] == "CX135")
    body = client.post("/api/planner/plan", json={"origin_id": "central", "flight_key": key}).json()
    assert body["deadline_kind"] == "Bag drop closes" and body["deadline"] == "2026-10-22T18:00:00+08:00"
    assert body["road_source"] == "airport_express"
    assert any("Airport Express timetable" in n for n in body["nudges"])
    assert body["leave_by"] < body["deadline"]
    assert [s["key"] for s in body["steps"]] == ["road", "checkin", "security", "walk"]
    assert body["labels"]["leave_by"] == "SIMULATED"


def test_plan_refuses_unknown_inputs(client):
    assert client.post("/api/planner/plan", json={"origin_id": "central", "flight_key": "nope"}).status_code == 404
    key = client.get("/api/planner/options").json()["flights"][0]["key"]
    assert client.post("/api/planner/plan", json={"origin_id": "mars", "flight_key": key}).status_code == 404


def test_road_time_maps_to_the_same_weekday_and_hour():
    when = datetime.fromisoformat("2026-10-22T18:40:00+08:00")      # a Thursday
    mapped = planner.road_time(when)
    assert mapped.isoformat() == "2026-11-19T18:00:00+08:00" and mapped.weekday() == when.weekday()
