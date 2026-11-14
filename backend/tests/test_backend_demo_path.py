"""GOLDEN: the demo story end to end over HTTP and WebSocket (AGENTS.md §3, §13 M7).

Mei (SYNTHETIC, Business) is on the real CX254 from London on 22 October 2026, connecting to the
real CX135 to Melbourne. No merge if this fails.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

HERO = "MEI-1"
T_MINUS_90 = "2026-10-22T16:51:00+08:00"   # 90 minutes before the estimated gate arrival (18:21)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("FLOW_TICK_SECONDS", "0.02")
    monkeypatch.setenv("FLOW_CLOCK_SECONDS", "60")
    monkeypatch.setenv("FLOW_PING_SECONDS", "60")
    with TestClient(create_app()) as test_client:
        yield test_client


def seek(client, t):
    reply = client.post("/api/replay/control", json={"action": "seek", "t": t})
    assert reply.status_code == 200, reply.text
    return reply.json()


def next_of(socket, kind):
    for _ in range(50):
        message = socket.receive_json()
        if message["type"] == kind:
            return message
    raise AssertionError(f"no {kind} message arrived")


def test_demo_story(client):
    # 1. The replay knows its hero and starts paused.
    state = client.get("/api/replay/state").json()
    assert state["hero_pid"] == HERO and state["playing"] is False
    assert state["start"] == "2026-10-22T05:30:00+08:00"   # before CX254 pushes back late in London

    trip = client.get(f"/api/passengers/{HERO}/trip").json()
    assert trip["passenger"]["cabin"] == "J" and trip["passenger"]["is_synthetic"] is True
    assert (trip["inbound"]["flight"], trip["inbound"]["origin"]) == ("CX254", "LHR")
    assert (trip["outbound"]["flight"], trip["outbound"]["dest"]) == ("CX135", "MEL")
    assert trip["sched_gap_min"] == 60

    # 2. Ninety minutes before landing her phone shows At risk, with a backup already held
    #    and her original seat still hers.
    assert seek(client, T_MINUS_90)["t"] == T_MINUS_90
    status = client.get(f"/api/passengers/{HERO}/protect").json()
    assert status["zone"] == "AT_RISK" and 0.30 <= status["p_miss"] <= 0.60
    assert status["inbound"]["status"] == "Airborne"
    assert status["inbound"]["est"] == "2026-10-22T18:21:00+08:00"     # OAG estimate, as published
    assert status["inbound"]["actual"] is None                        # not known yet
    assert status["gate_close"] == "2026-10-22T18:45:00+08:00"         # 19:00 departure - 15 min
    assert status["minutes_available"] == 20       # 18:45 close - (18:21 estimate + 4 min measured bias)
    low, high = status["minutes_needed"]
    assert 15 <= low < high <= 40
    assert status["backup_hold"]["flight"] == "CX105"
    assert status["original_seat_held"] is True
    assert status["state"] == "DRAFT_PENDING"
    assert status["drivers"][0]["key"] == "inbound_delay"

    options = client.get(f"/api/passengers/{HERO}/options").json()
    assert [o["kind"] for o in options] == ["ORIGINAL_EXPEDITE", "ALT_FLIGHT", "OVERNIGHT"]
    assert [o["flight"] for o in options] == ["CX135", "CX105", "CX163"]
    assert [o["approved"] for o in options] == [True, False, False]
    assert options[0]["guaranteed"] is False and options[1]["guaranteed"] is True
    alt = next(o for o in options if o["kind"] == "ALT_FLIGHT")
    # Not approved yet, so she cannot take it.
    assert client.post(f"/api/passengers/{HERO}/choose", json={"option_id": alt["option_id"]}).status_code == 409

    # 3. The staff console shows the wave and the drafted rebookings, each with a reason.
    wave = client.get("/api/staff/wave").json()
    assert wave["summary"]["drafts_pending"] > 5 and wave["summary"]["at_risk"] > 5
    assert any(row["pid"] == HERO for row in wave["connections"])
    drafts = client.get("/api/staff/drafts", params={"status": "PENDING"}).json()
    mine = next(d for d in drafts if d["pid"] == HERO)
    assert "CX135" in mine["rationale"] and "CX105" in mine["rationale"] and "Mei Chen" in mine["rationale"]

    # 4. Staff approve the batch in one click; both screens hear about it.
    with client.websocket_connect(f"/ws?role=passenger&pid={HERO}") as phone, \
            client.websocket_connect("/ws?role=staff") as console:
        approved = client.post("/api/staff/drafts/approve-batch", json={"ids": [d["draft_id"] for d in drafts]})
        assert approved.status_code == 200 and len(approved.json()) == len(drafts)
        assert next_of(phone, "notification")["payload"]["title"] == "Your options are ready"
        assert next_of(phone, "options_update")["payload"]["options"]
        assert next_of(console, "draft_update")["payload"]["status"] == "APPROVED"

        status = client.get(f"/api/passengers/{HERO}/protect").json()
        assert status["state"] == "OFFERED" and status["original_seat_held"] is True
        options = client.get(f"/api/passengers/{HERO}/options").json()
        assert all(o["approved"] for o in options)

        # 5. Mei chooses the held seat before she lands; the console updates.
        chosen = client.post(f"/api/passengers/{HERO}/choose", json={"option_id": alt["option_id"]})
        assert chosen.status_code == 200
        body = chosen.json()
        assert body["state"] == "REBOOKED" and body["original_seat_held"] is False
        assert body["backup_hold"]["flight"] == "CX105"
        update = next_of(console, "connection_update")
        while update["payload"]["pid"] != HERO or update["payload"]["state"] == "OFFERED":
            update = next_of(console, "connection_update")   # skip the approval's own update
        assert update["payload"]["state"] == "REBOOKED"
        update = next_of(phone, "connection_update")
        if update["payload"]["state"] == "OFFERED":
            update = next_of(phone, "connection_update")
        assert update["payload"]["state"] == "REBOOKED"

    # Settled: she cannot choose again.
    again = client.post(f"/api/passengers/{HERO}/choose", json={"option_id": alt["option_id"]})
    assert again.status_code == 409


def test_single_approve_and_reject(client):
    seek(client, T_MINUS_90)
    drafts = client.get("/api/staff/drafts", params={"status": "PENDING"}).json()
    first, second = drafts[0], drafts[1]
    reply = client.post(f"/api/staff/drafts/{first['draft_id']}", json={"decision": "approve"})
    assert reply.json()["status"] == "APPROVED"
    reply = client.post(f"/api/staff/drafts/{second['draft_id']}", json={"decision": "reject", "note": "seat needed"})
    assert reply.json()["status"] == "REJECTED" and reply.json()["note"] == "seat needed"
    # A rejected draft leaves the backup held and nothing changes for the passenger.
    status = client.get(f"/api/passengers/{second['pid']}/protect").json()
    assert status["state"] == "BACKUP_HELD" and status["backup_hold"] and status["original_seat_held"]
    assert client.post(f"/api/staff/drafts/{first['draft_id']}", json={"decision": "approve"}).status_code == 409
    assert client.post("/api/staff/drafts/D9999", json={"decision": "approve"}).status_code == 404


def test_play_pushes_the_clock_and_updates(client):
    seek(client, "2026-10-22T17:10:00+08:00")
    with client.websocket_connect("/ws?role=staff") as console:
        client.post("/api/replay/control", json={"action": "speed", "speed": 600})
        assert client.post("/api/replay/control", json={"action": "play"}).json()["playing"] is True
        clocks = [next_of(console, "clock") for _ in range(4)]
        assert clocks[-1]["payload"]["t"] > clocks[0]["payload"]["t"]
        # CX443 from Taipei leaves late inside this window: its passengers' status changes.
        seen = [next_of(console, "connection_update") for _ in range(3)]
        assert all("p_miss" in message["payload"] for message in seen)
        client.post("/api/replay/control", json={"action": "pause"})
    assert client.get("/api/replay/state").json()["playing"] is False


def test_unknown_passenger_and_scenarios(client):
    assert client.get("/api/passengers/NOBODY/protect").status_code == 404
    assert client.get("/api/passengers/NOBODY/trip").status_code == 404
    assert client.get("/api/scenarios").json() == [
        {"id": "2026-10-22-evening", "title": "Thursday 22 October 2026, evening wave at Hong Kong"}]
    assert client.post("/api/replay/load", json={"scenario_id": "nope"}).status_code == 404


def test_mei_turns_at_risk_when_cx254_leaves_london_late(client):
    """The slip happens on screen: OAG published the late pushback at 05:37 HKT."""
    before = seek(client, "2026-10-22T05:36:00+08:00")
    status = client.get(f"/api/passengers/{HERO}/protect").json()
    assert before["t"] == "2026-10-22T05:36:00+08:00"
    assert status["zone"] == "SAFE" and status["backup_hold"] is None
    assert status["inbound"]["status"] == "Scheduled"

    seek(client, "2026-10-22T05:40:00+08:00")
    status = client.get(f"/api/passengers/{HERO}/protect").json()
    assert status["zone"] == "AT_RISK" and status["inbound"]["status"] == "Airborne"
    assert status["inbound"]["est"] == "2026-10-22T18:23:00+08:00"
    assert status["backup_hold"]["flight"] == "CX105" and status["original_seat_held"] is True
