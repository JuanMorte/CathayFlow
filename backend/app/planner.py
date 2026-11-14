"""Gate Planner service: times to the airport for the engine, and the list of choices (AGENTS.md §12).

Drive, train and bus times come from Google Routes through the read-through cache (flowcore.sources).
Google only quotes traffic and timetables for the future, so a replay time is mapped to the same
weekday and hour on a fixed future date (ROAD_DATE), rounded to the hour so a small set of cached
answers covers the evening. Any failure (offline cache miss, rejected key, budget, network, no
route) falls back to the Airport Express timetable, and the plan says so.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import yaml

from flowcore.config import find_repo_root
from flowcore.engine.gate_planner import Road, airport_express, gate_at
from flowcore.sources import google_routes

log = logging.getLogger(__name__)

# A Thursday, like the scenario day (22 Oct 2026), after the hackathon starts. Fixed so cached road
# times stay valid; after this date live calls fail and the planner uses the timetable.
ROAD_DATE = date(2026, 11, 19)


@lru_cache(maxsize=1)
def origins() -> list[dict]:
    file: Path = find_repo_root() / "data" / "reference" / "planner_origins.yaml"
    return yaml.safe_load(file.read_text(encoding="utf-8"))["origins"]


def origin(origin_id: str) -> dict:
    found = next((o for o in origins() if o["id"] == origin_id), None)
    if not found:
        raise KeyError(origin_id)
    return found


def road_time(when: datetime) -> datetime:
    """Same weekday and hour on ROAD_DATE's week (the replay day may be in the past)."""
    shift = (ROAD_DATE.weekday() - when.weekday()) % 7
    day = ROAD_DATE + timedelta(days=shift)
    return when.replace(year=day.year, month=day.month, day=day.day, minute=0, second=0, microsecond=0)


def google_road(origin_id: str, when: datetime, config: dict) -> Road:
    place = origin(origin_id)
    at = road_time(when)
    upper = google_routes.compute_route(place["address"], at, traffic_model="PESSIMISTIC")
    typical = google_routes.compute_route(place["address"], at, traffic_model="BEST_GUESS")
    t_min = google_routes.duration_seconds(typical) / 60
    u_min = max(google_routes.duration_seconds(upper) / 60, t_min)
    free_flow = google_routes.duration_seconds(typical, "staticDuration")
    fastest = min(t_min, free_flow / 60 if free_flow else t_min) * config["planner"]["fastest_share"]
    return Road(t_min, u_min, "google",
                f"Google traffic model for {at:%a} {at:%H:%M} (same weekday and hour)", "REAL", floor=fastest)


# Which vehicles Google may use for each planner mode. RAIL covers the MTR lines and the Airport Express.
TRANSIT_MODES = {"train": ("RAIL",), "bus": ("BUS",)}


def google_transit(origin_id: str, mode: str, when: datetime, config: dict) -> Road:
    """A train or bus trip from Google's timetables, with our ASSUMED upper end (config `planner.transit`)."""
    place = origin(origin_id)
    at = road_time(when)
    envelope = google_routes.compute_route(place["address"], at, travel_mode="TRANSIT",
                                           transit_modes=TRANSIT_MODES[mode])
    seconds = google_routes.duration_seconds(envelope)
    rides = google_routes.transit_lines(envelope)
    if seconds is None or not rides:
        raise LookupError(f"Google has no {mode} route from {place['name']}.")
    spec = config["planner"]["transit"][mode]
    typical = seconds / 60
    upper = typical + spec["extra_upper"]
    if mode == "bus":
        try:
            drive = google_road(origin_id, when, config)
            ratio = drive.upper / drive.typical
        except Exception:  # no cached drive for this hour: the documented default
            ratio = spec["traffic_ratio_default"]
        upper += sum(ride["seconds"] for ride in rides) / 60 * (ratio - 1)
    names = list(dict.fromkeys(ride["name"] for ride in rides if ride["name"]))
    return Road(typical, upper, "google_transit",
                f"Google timetable for {at:%a} {at:%H:%M}: {', then '.join(names)}", "REAL",
                floor=typical * config["planner"]["fastest_share"])


def road_for(origin_id: str, mode: str, config: dict):
    def lookup(when: datetime) -> Road:
        try:
            if mode in TRANSIT_MODES:
                return google_transit(origin_id, mode, when, config)
            return google_road(origin_id, when, config)
        except Exception as err:  # any failure: the timetable, and the plan says so
            log.info("%s time unavailable (%s); using the Airport Express timetable", mode, type(err).__name__)
            return airport_express(config)
    return lookup


def flight_choices(flights: dict, t: datetime, limit: int = 30) -> list[dict]:
    """Departures with a published status history, leaving at least an hour after t."""
    found = [f for f in flights.values()
             if f["kind"] == "dep" and f.get("timeline") and not f.get("cancelled")
             and f["sched"] >= t + timedelta(hours=1)]
    found.sort(key=lambda f: f["sched"])
    return [{"key": f["key"], "flight": f["flight"], "dest": f["airport"], "dest_city": f.get("city", f["airport"]),
             "sched": f["sched"], "gate": gate_at(f, t)} for f in found[:limit]]
