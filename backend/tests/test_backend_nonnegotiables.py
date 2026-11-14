"""GOLDEN: one test per non-negotiable (AGENTS.md §2). No merge if any of these fail."""

import copy
import re
from datetime import datetime, timedelta, timezone

import pytest

from app.policy import seats as seat_rules
from app.policy.seats import OriginalSeatError, Seats
from app.replay.sim import PolicyError, Sim, load_policy

SCENARIO = "2026-10-22-evening"
HKT = timezone(timedelta(hours=8))
LABELS = {"REAL", "ASSUMED", "SYNTHETIC", "SIMULATED"}


def at(hour, minute=0):
    return datetime(2026, 10, 22, hour, minute, tzinfo=HKT)


@pytest.fixture
def sim():
    return Sim(SCENARIO)


def approve_all(sim):
    for draft in sim.draft_list("PENDING"):
        sim.decide(draft["draft_id"], "approve")


# 1. The original seat is never released early. -------------------------------------------

def test_original_seat_guard_refuses_every_other_path(sim):
    mei = sim.by_pid["MEI-1"]
    gate_close = mei.assessment.gate_close
    for reason in ("backup_held", "agent_rebooked", "passenger_chose_alternative"):
        with pytest.raises(OriginalSeatError):
            seat_rules.release_original_seat(mei, reason, sim.t, gate_close)
    with pytest.raises(OriginalSeatError):   # gate close has not passed
        seat_rules.release_original_seat(mei, seat_rules.GATE_CLOSED, gate_close - timedelta(minutes=1), gate_close)
    assert mei.original_seat_held is True


def test_original_seats_through_a_whole_replay(sim):
    """Holds, drafts and an agent's rebooking never release a seat: only a missed gate close does."""
    t = sim.start
    rebooked_before_close = 0
    while t < sim.end:
        t += timedelta(minutes=10)
        sim.advance_to(t)
        approve_all(sim)
        for ps in sim.parties.values():
            if ps.state == "AGENT_REBOOKED":
                rebooked_before_close += 1
                assert ps.original_seat_held and ps.booked and sim.t < ps.assessment.gate_close
            if ps.original_seat_held:
                continue
            assert ps.release_reason == seat_rules.GATE_CLOSED
            assert ps.outcome == "MISSED" and ps.assessment.gate_close <= sim.t
    assert rebooked_before_close > 10
    released = [ps for ps in sim.parties.values() if not ps.original_seat_held]
    assert released, "the scenario should contain missed connections"
    for ps in sim.parties.values():
        if ps.outcome == "MADE":
            # Rebooked or not, a passenger who makes the original flight flies it, and the later seat is freed.
            assert ps.original_seat_held and ps.state == "MADE_ORIGINAL" and ps.hold is None and ps.booked is None


def test_rebooked_passenger_who_makes_it_keeps_the_original():
    """The auto-rebook problem: an agent rebooks, the passenger makes the original after all."""
    sim = Sim(SCENARIO)
    t = sim.start
    while t < sim.end:
        t += timedelta(minutes=10)
        sim.advance_to(t)
        approve_all(sim)
    rebooked = [ps for ps in sim.parties.values() if ps.decision == "REBOOK"]
    made = [ps for ps in rebooked if ps.outcome == "MADE"]
    assert made, "some rebooked passengers should have made the original flight"
    assert all(ps.state == "MADE_ORIGINAL" and ps.original_seat_held and ps.booked is None for ps in made)
    assert any(entry["kind"] == "hold_released" and entry["why"] == "made the original flight" for entry in sim.log)


# 2. No rebooking without staff approval. -------------------------------------------------

def test_nothing_is_booked_before_an_agent_decides(sim):
    sim.seek(at(16, 51))
    mei = sim.by_pid["MEI-1"]
    assert mei.hold and mei.state == "DRAFT_PENDING" and mei.booked is None and mei.decision is None
    assert all(ps.booked is None for ps in sim.parties.values())
    sim.decide(mei.draft_id, "approve")
    assert mei.state == "AGENT_REBOOKED" and mei.booked["flight_no"] == "CX105" and mei.hold is None
    assert mei.decision == "REBOOK" and mei.decided_at == sim.t and mei.original_seat_held
    with pytest.raises(PolicyError, match="already"):
        sim.decide(mei.draft_id, "approve")


def test_keep_leaves_the_hold_and_is_not_drafted_again(sim):
    sim.seek(at(16, 51))
    mei = sim.by_pid["MEI-1"]
    sim.decide(mei.draft_id, "reject", "seat needed elsewhere")
    assert mei.state == "BACKUP_HELD" and mei.hold["flight_no"] == "CX105" and mei.decision == "KEEP"
    sim.advance_to(at(17, 30))
    assert sim.drafts[mei.draft_id]["status"] == "REJECTED"
    assert sum(1 for d in sim.drafts.values() if d["party_id"] == "MEI") == 1
    assert any(entry["kind"] == "draft_reject" for entry in sim.log)


# 3. The passenger is told at once; nothing is rebooked silently. ---------------------------

def test_a_hold_is_not_a_booking_and_every_rebooking_is_announced(sim):
    t = sim.start
    told = set()
    while t < at(18, 0):
        t += timedelta(minutes=10)
        sim.advance_to(t)
        for draft in sim.draft_list("PENDING"):
            events = sim.decide(draft["draft_id"], "approve")
            notes = [e for e in events if e["type"] == "notification"]
            assert len(notes) == 1 and notes[0]["payload"]["title"] == "Your connection has changed"
            assert draft["alt_flight"] in notes[0]["payload"]["body"] and draft["pid"] in notes[0]["pids"]
            told.add(draft["connection_id"])
        for ps in sim.parties.values():
            if ps.state == "AGENT_REBOOKED":
                assert ps.party["party_id"] in told
            elif ps.state == "REBOOKED" and ps.party["party_id"] not in told:
                # Without an agent, the only way here is a held seat converted after the miss.
                assert ps.auto_converted and ps.outcome == "MISSED" and ps.assessment.gate_close <= sim.t
            elif ps.hold:
                assert ps.booked is None and ps.original_seat_held
    assert len(told) > 10


def test_mei_after_the_agent_rebooks(sim):
    sim.seek(at(16, 51))
    mei = sim.by_pid["MEI-1"]
    sim.decide(mei.draft_id, "approve")
    sim.advance_to(at(18, 50))    # past her 18:45 gate close: the ground truth decides
    assert mei.outcome in ("MADE", "MISSED")
    if mei.outcome == "MADE":
        assert mei.state == "MADE_ORIGINAL" and mei.original_seat_held and mei.booked is None
    else:
        assert mei.state == "REBOOKED" and mei.booked["flight_no"] == "CX105"
        assert mei.release_reason == seat_rules.GATE_CLOSED and not mei.auto_converted


# 4. Hard fairness rules beat scores. -----------------------------------------------------

def test_a_party_is_never_split():
    # A350-900 Business: 38 seats x (1 - 0.872) = 4.9 -> 4 free.
    seats = Seats(load_policy(), {"X": {"cabin_seats": {"F": 0, "J": 38, "W": 28, "Y": 214}}}, 0.872)
    assert seats.free("X", "J") == 4 and seats.free("X", "Y") == 27 and seats.free("X", "F") == 0
    assert seats.take("X", "J", 5, at(16)) is False       # family of five, four seats: nobody moves
    assert seats.free("X", "J") == 4
    assert seats.take("X", "J", 4, at(16)) is True and seats.free("X", "J") == 0
    assert Seats(load_policy()).free("unknown", "J") == 3  # fallback for an unknown aircraft


def test_assistance_first_and_tier_is_only_a_weight(sim):
    sim.seek(at(16, 51))
    waiting = [ps for ps in sim.parties.values() if ps.zone != "SAFE" and not ps.final][:3]
    assert len(waiting) == 3
    low, high, helper = waiting
    for ps in waiting:                      # put all three back in the queue
        if ps.hold:
            sim._release_hold(ps, "test")
        ps.state, ps.draft_id = "MONITORING", None
        ps.party = copy.deepcopy(ps.party)
        ps.party["cabin"] = "Y"
    low.party.update(tier="Diamond", assistance=False)
    high.party.update(tier="Green", assistance=False)
    helper.party.update(tier="None", assistance=True)
    low.assessment = low.assessment.__class__(0.30, *list(low.assessment.__dict__.values())[1:])
    high.assessment = high.assessment.__class__(0.95, *list(high.assessment.__dict__.values())[1:])
    helper.assessment = helper.assessment.__class__(0.25, *list(helper.assessment.__dict__.values())[1:])
    order = [ps for ps in sim._hold_queue() if ps in waiting]
    assert order[0] is helper                 # declared assistance needs always go first
    assert order.index(high) < order.index(low)   # Diamond at 30% does not jump Green at 95%


def test_every_hold_and_booking_covers_the_whole_party(sim):
    sim.advance_to(at(18, 30))
    approve_all(sim)
    held = {}
    for ps in sim.parties.values():
        seat = ps.hold or ps.booked
        if seat:
            key = (seat["flight_key"], seat["cabin"])
            held[key] = held.get(key, 0) + ps.size
    assert held == {key: count for key, count in sim.seats.taken.items() if count}


# 5. No invented facts: the rationale is a template over the draft's own fields. -----------

def test_rationale_numbers_and_flights_match_the_draft(sim):
    sim.seek(at(17, 30))
    drafts = sim.draft_list()
    assert len(drafts) > 20
    for draft in drafts:
        ps = sim.parties[draft["connection_id"]]
        text = draft["rationale"]
        assert set(re.findall(r"CX\d+[A-Z]?", text)) == {draft["outbound_flight"], draft["alt_flight"]}
        assert re.search(r"(\d+)% likely to miss", text)[1] == f"{draft['p_miss'] * 100:.0f}"
        times = re.findall(r"\b\d{2}:\d{2}\b", text)
        expected = [f"{draft['alt_dep']:%H:%M}"] + ([f"{draft['alt_arrival']:%H:%M}"] if draft["alt_arrival"] else [])
        assert times == expected
        assert text.startswith(ps.name)
        size = re.search(r"group of (\d+)", text)
        assert (int(size[1]) if size else 1) == draft["group_size"]


# 6. Real vs synthetic is always visible. -------------------------------------------------

def test_every_payload_carries_labels(sim):
    sim.seek(at(16, 51))
    wave = sim.wave()
    payloads = [wave["summary"], *wave["summary"]["inbounds"], *wave["connections"],
                *sim.draft_list(), sim.trip("MEI-1"),
                sim.trip("MEI-1")["passenger"]]
    for row in wave["connections"]:
        payloads += [row["inbound"], row["outbound"]]
    for payload in payloads:
        assert payload["labels"] and set(payload["labels"].values()) <= LABELS
    status = sim.status_view(sim.by_pid["MEI-1"])
    assert status["labels"]["p_miss"] == "SIMULATED" and status["labels"]["passenger_name"] == "SYNTHETIC"
    assert status["inbound"]["labels"]["sched"] == "REAL"
    assert status["labels"]["minutes_needed"] == "ASSUMED"


# 7. No leakage. --------------------------------------------------------------------------

@pytest.mark.parametrize("now", [at(16, 30), at(17, 15), at(18, 5), at(18, 40)])
def test_the_future_cannot_change_what_is_shown_now(sim, now):
    """Rewrite everything that happens after `now`: what is known at `now` must not move."""
    baseline = Sim(SCENARIO)
    baseline.advance_to(now)
    for flight in sim.flights.values():
        if flight["actual"] and flight["actual"] > now:
            flight["actual"] += timedelta(minutes=47)
        for event in flight["timeline"]:
            if event["at"] > now:
                event["est"] = event["est"] + timedelta(minutes=47) if event["est"] else None
                event["state"] = "InGate"
    sim.reset()
    sim.advance_to(now)
    assert sim.wave() == baseline.wave()
    assert sim.draft_list() == baseline.draft_list()
    for ps in sim.parties.values():
        for view in (ps.in_view, ps.out_view):
            assert view.actual is None or view.actual <= now


def test_same_seed_same_replay():
    first, second = Sim(SCENARIO), Sim(SCENARIO)
    first.advance_to(at(18, 0))
    second.advance_to(at(18, 0))
    assert first.wave() == second.wave() and first.log == second.log
