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
    with pytest.raises(OriginalSeatError):
        seat_rules.release_original_seat(mei, "backup_held", sim.t, gate_close)
    with pytest.raises(OriginalSeatError):   # gate close has not passed
        seat_rules.release_original_seat(mei, seat_rules.GATE_CLOSED, gate_close - timedelta(minutes=1), gate_close)
    with pytest.raises(OriginalSeatError):   # no explicit choice was made
        seat_rules.release_original_seat(mei, seat_rules.PASSENGER_CHOSE, sim.t, gate_close)
    assert mei.original_seat_held is True


def test_original_seats_through_a_whole_replay(sim):
    """Holds, drafts and approvals never release a seat: only a choice or a missed gate close does."""
    t = sim.start
    while t < sim.end:
        t += timedelta(minutes=10)
        sim.advance_to(t)
        approve_all(sim)
        for ps in sim.parties.values():
            if ps.original_seat_held:
                continue
            assert ps.release_reason == seat_rules.GATE_CLOSED      # nobody chose in this run
            assert ps.outcome == "MISSED" and ps.assessment.gate_close <= sim.t
    released = [ps for ps in sim.parties.values() if not ps.original_seat_held]
    assert released, "the scenario should contain missed connections"
    for ps in sim.parties.values():
        if ps.outcome == "MADE":
            assert ps.original_seat_held and ps.state == "MADE_ORIGINAL" and ps.hold is None


# 2. No rebooking without staff approval. -------------------------------------------------

def test_unapproved_options_cannot_be_chosen(sim):
    sim.seek(at(16, 51))
    mei = sim.by_pid["MEI-1"]
    assert mei.hold and mei.state == "DRAFT_PENDING"
    kinds = {option["kind"]: option for option in sim.options("MEI-1")}
    assert kinds["ALT_FLIGHT"]["approved"] is False and kinds["OVERNIGHT"]["approved"] is False
    for kind in ("ALT_FLIGHT", "OVERNIGHT"):
        with pytest.raises(PolicyError, match="not been approved"):
            sim.choose("MEI-1", kinds[kind]["option_id"])
    assert mei.state == "DRAFT_PENDING" and mei.original_seat_held and mei.booked is None


def test_rejection_keeps_the_hold_and_is_not_drafted_again(sim):
    sim.seek(at(16, 51))
    mei = sim.by_pid["MEI-1"]
    sim.decide(mei.draft_id, "reject", "seat needed elsewhere")
    assert mei.state == "BACKUP_HELD" and mei.hold["flight_no"] == "CX105"
    sim.advance_to(at(17, 30))
    assert sim.drafts[mei.draft_id]["status"] == "REJECTED"
    assert sum(1 for d in sim.drafts.values() if d["party_id"] == "MEI") == 1
    with pytest.raises(PolicyError):
        sim.choose("MEI-1", "MEI:ALT_FLIGHT")
    assert any(entry["kind"] == "draft_reject" for entry in sim.log)


# 3. The passenger chooses. ---------------------------------------------------------------

def test_a_hold_is_not_a_booking_and_nothing_is_rebooked_silently(sim):
    t = sim.start
    while t < at(18, 0):
        t += timedelta(minutes=10)
        sim.advance_to(t)
        approve_all(sim)
        for ps in sim.parties.values():
            if ps.state == "REBOOKED":
                # Without a choice, the only way here is a held seat converted after the miss.
                assert ps.auto_converted and ps.outcome == "MISSED" and ps.assessment.gate_close <= sim.t
            elif ps.hold:
                assert ps.booked is None and ps.original_seat_held
    assert sum(1 for ps in sim.parties.values() if ps.hold) > 10


def test_choosing_the_original_keeps_everything(sim):
    sim.seek(at(16, 51))
    approve_all(sim)
    sim.choose("MEI-1", "MEI:ORIGINAL_EXPEDITE")
    mei = sim.by_pid["MEI-1"]
    assert mei.state == "PASSENGER_CHOSE" and mei.original_seat_held and mei.hold["flight_no"] == "CX105"
    sim.advance_to(at(18, 50))    # past her 18:45 gate close: the ground truth decides
    assert mei.outcome in ("MADE", "MISSED")
    if mei.outcome == "MADE":
        assert mei.state == "MADE_ORIGINAL" and mei.original_seat_held and mei.hold is None
    else:
        assert mei.state == "REBOOKED" and mei.booked["flight_no"] == "CX105"
        assert mei.release_reason == seat_rules.GATE_CLOSED


# 4. Hard fairness rules beat scores. -----------------------------------------------------

def test_a_party_is_never_split():
    seats = Seats(load_policy(), at(16))
    assert seats.free("X", "J", at(16)) == 3
    assert seats.take("X", "J", 4, at(16)) is False       # family of four, three seats: nobody moves
    assert seats.free("X", "J", at(16)) == 3
    assert seats.take("X", "J", 3, at(16)) is True and seats.free("X", "J", at(16)) == 0


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
        seat = ps.hold or (ps.booked if ps.state == "REBOOKED" else None)
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
        text, option = draft["rationale"], draft["option"]
        assert set(re.findall(r"CX\d+[A-Z]?", text)) == {draft["outbound_flight"], option["flight"]}
        assert re.search(r"(\d+)% likely to miss", text)[1] == f"{draft['p_miss'] * 100:.0f}"
        times = re.findall(r"\b\d{2}:\d{2}\b", text)
        expected = [f"{option['dep']:%H:%M}"] + ([f"{option['final_arrival']:%H:%M}"] if option["final_arrival"] else [])
        assert times == expected
        assert text.startswith(ps.name)
        size = re.search(r"group of (\d+)", text)
        assert (int(size[1]) if size else 1) == draft["group_size"]


# 6. Real vs synthetic is always visible. -------------------------------------------------

def test_every_payload_carries_labels(sim):
    sim.seek(at(16, 51))
    wave = sim.wave()
    payloads = [wave["summary"], *wave["summary"]["inbounds"], *wave["connections"],
                *sim.draft_list(), *sim.options("MEI-1"), sim.trip("MEI-1"),
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
