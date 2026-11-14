"""Gate Planner: when to leave for the airport (AGENTS.md §12).

    door_to_gate = road + check-in/bag drop (0 if online and no bags) + immigration and security + walk
    deadline     = bag drop close (departure - 60 min) with checked bags, else gate close (departure - 15 min)
    leave_by     = deadline - door_to_gate at the chosen percentile

The leg to the airport comes from a function the caller passes in (Google Routes through the cache:
a drive, or a train or bus trip; or the Airport Express timetable when Google has no answer), so the
engine itself makes no network calls. Everything else is in
config/engine.yaml (`planner`) with its source. Only what is published at time t is used: the
departure time moves only once the airline publishes a delay, and the gate counts only once it
has been published.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable

import numpy as np

from flowcore.engine.asof import outbound_view
from flowcore.engine.time_to_gate import rng_for
from flowcore.engine.zones import Zones

PERCENTILE_KEYS = ("relaxed", "balanced", "tight")


@dataclass(frozen=True)
class Road:
    """Door to the terminal: typical and upper minutes, and where they came from."""
    typical: float
    upper: float
    source: str        # "google" (drive) | "google_transit" (train or bus) | "airport_express" (timetable)
    note: str
    label: str         # REAL (Google) | ASSUMED (our timetable)
    floor: float | None = None   # fastest possible minutes; None = 60% of typical


@dataclass(frozen=True)
class PlanRequest:
    origin_id: str
    flight_key: str
    bags: int = 1
    checked_in_online: bool = False
    hk_resident: bool = True
    mode: str = "car"                  # car | train | bus
    buffer: str = "balanced"           # relaxed | balanced | tight


@dataclass
class Plan:
    flight: str
    dest_city: str
    sched_departure: datetime
    departure: datetime                # published departure as of t
    gate: str | None                   # published gate as of t
    deadline: datetime
    deadline_kind: str                 # "Bag drop closes" | "Gate closes"
    leave_by: datetime
    percentile: int
    typical_total: int
    upper_total: int
    steps: list[dict] = field(default_factory=list)
    road_source: str = ""
    road_note: str = ""
    nudges: list[str] = field(default_factory=list)


def gate_at(flight: dict, t: datetime) -> str | None:
    """The departure gate as published at t (OAG timeline); None before it is published.
    Flights without a timeline fall back to the HKIA record (treated as known, AGENTS.md §17.4.7)."""
    events = flight.get("timeline") or []
    if not events:
        return flight.get("gate")
    gate = None
    for event in events:
        if event["at"] <= t and event.get("gate"):
            gate = event["gate"]
    return gate


def _normal(rng: np.random.Generator, spec: dict, n: int) -> np.ndarray:
    return np.maximum(rng.normal(spec["mean"], spec["sd"], n), spec.get("floor", 0.0))


def road_samples(road: Road, config: dict, rng: np.random.Generator, n: int) -> np.ndarray:
    """Typical as the median and upper as the 95th percentile of a normal, never below the road's
    floor (the no-traffic drive or the timetable; 60% of typical when the road gives none)."""
    z = 1.6449  # 95th percentile of a standard normal
    sd = max((road.upper - road.typical) / z, 1.0)
    floor = road.floor if road.floor is not None else road.typical * 0.6
    return np.maximum(rng.normal(road.typical, sd, n), floor)


def airport_express(config: dict) -> Road:
    express = config["planner"]["airport_express"]
    to_station = express["to_station"]
    typical = to_station["mean"] + express["headway"] / 2 + express["ride"]
    upper = to_station["mean"] + 1.645 * to_station["sd"] + express["headway"] + express["ride"]
    return Road(typical, upper, "airport_express",
                f"Airport Express: {express['ride']} min ride, a train every {express['headway']} min",
                "ASSUMED")


def plan(request: PlanRequest, flight: dict, t: datetime, config: dict, zones: Zones,
         road_for: Callable[[datetime], Road], seed: int) -> Plan:
    p = config["planner"]
    n = int(config["samples"])
    rng = rng_for(seed, "planner", request.origin_id, request.flight_key, request.mode, str(request.bags))

    view = outbound_view(flight, t)
    departure = view.time
    gate = gate_at(flight, t)
    with_bags = request.bags > 0
    if with_bags:
        deadline, kind = departure - timedelta(minutes=p["bag_drop_close_minutes"]), "Bag drop closes"
    else:
        deadline, kind = departure - timedelta(minutes=config["gate_close_minutes"]), "Gate closes"

    # Check-in and bag drop: nothing if checked in online with no bags to drop.
    if request.checked_in_online and not with_bags:
        checkin = np.zeros(n)
    else:
        hour = (deadline - timedelta(minutes=60)).hour
        peak = any(low <= hour < high for low, high in p["checkin_queue"]["peak_hours"])
        checkin = _normal(rng, p["checkin_queue"]["peak" if peak else "offpeak"], n)
    security = _normal(rng, p["security_resident" if request.hk_resident else "security_visitor"], n)

    # Walk from the check-in hall to the gate; an unpublished gate uses the default zone.
    end_zone = zones.gate(gate).zone if gate else p["unknown_gate_zone"]
    walk_m = zones.walk_m(p["start_zone"], end_zone)
    walk = walk_m / _normal(rng, config["walk_speed"], n) / 60.0
    train = zones.train_minutes(p["start_zone"], end_zone)
    if train:
        walk = walk + np.maximum(rng.normal(train, config["train_sd"], n), train / 2)

    # The road depends on when you leave, and when you leave depends on the road: two passes.
    percentile = int(p["percentiles"][request.buffer])
    first_guess = deadline - timedelta(minutes=90)
    road = road_for(first_guess)
    for _ in range(2):
        total = road_samples(road, config, rng_for(seed, "road", request.origin_id), n) + checkin + security + walk
        leave_by = deadline - timedelta(minutes=float(np.percentile(total, percentile)))
        next_road = road_for(leave_by)
        if (next_road.typical, next_road.upper) == (road.typical, road.upper):
            break
        road = next_road
    road_minutes = road_samples(road, config, rng_for(seed, "road", request.origin_id), n)
    total = road_minutes + checkin + security + walk
    leave_by = deadline - timedelta(minutes=float(np.percentile(total, percentile)))
    leave_by = leave_by.replace(minute=leave_by.minute - leave_by.minute % 5, second=0, microsecond=0)

    def step(key: str, title: str, values: np.ndarray, label: str, note: str) -> dict:
        return {"key": key, "title": title, "typical": int(round(float(np.median(values)))),
                "upper": int(round(float(np.percentile(values, 95)))), "label": label, "note": note}

    resident = "e-Channel for residents" if request.hk_resident else "Immigration pledge: 95% of visitors within 15 min"
    steps = [
        step("road", "To the airport", road_minutes, road.label, road.note),
        step("checkin", "Check-in and bag drop", checkin, "ASSUMED",
             "Checked in online, no bags" if not checkin.any() else "Queue at this hour"),
        step("security", "Immigration and security", security, "ASSUMED", resident),
        step("walk", f"Walk to gate {gate}" if gate else "Walk to your gate", walk, "ASSUMED",
             f"{int(walk_m)} m from check-in" + (" plus the train" if train else "")
             + ("" if gate else "; planned for a far gate until it is published")),
    ]
    nudges = []
    if not request.checked_in_online:
        nudges.append("Check in online to skip the counter queue.")
    if request.mode == "car" and road.source == "airport_express":
        nudges.append("Road times are unavailable; this plan uses the Airport Express timetable.")
    if request.mode == "bus" and road.source == "airport_express":
        nudges.append("Bus times are unavailable; this plan uses the Airport Express timetable.")
    if view.est and view.est > flight["sched"]:
        nudges.append(f"{flight['flight']} now leaves at {departure:%H:%M}; your plan has moved with it.")
    return Plan(
        flight=flight["flight"], dest_city=flight.get("city", flight["airport"]), sched_departure=flight["sched"],
        departure=departure, gate=gate, deadline=deadline, deadline_kind=kind, leave_by=leave_by,
        percentile=percentile, typical_total=int(round(float(np.median(total)))),
        upper_total=int(round(float(np.percentile(total, 95)))), steps=steps,
        road_source=road.source, road_note=road.note, nudges=nudges,
    )
