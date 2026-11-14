"""Tables for the research notebooks, read from what is already stored in data/ (no network calls)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yaml

from flowcore.config import get_settings
from flowcore.engine.gate_planner import Road
from flowcore.engine.zones import Zones
from flowcore.parse.hkia import HKT, delay_minutes, parse_envelopes
from flowcore.sources import google_routes


def google_roads() -> pd.DataFrame:
    """One row per starting point and hour: the cached Google Routes answers for the drive to Terminal 1.

    `typical` is Google's BEST_GUESS traffic model, `upper` its PESSIMISTIC one, `free_flow` the drive with no
    traffic (`staticDuration`); all in minutes. Replies outside the planner's grid (the API check) are left out.
    """
    settings = get_settings()
    origins = yaml.safe_load((settings.repo_root / "data" / "reference" / "planner_origins.yaml").read_text())
    names = {o["address"]: o["name"] for o in origins["origins"]}
    found: dict[tuple, dict] = {}
    for file in sorted((settings.data_dir / "raw" / "google").glob("*.json")):
        envelope = json.loads(file.read_text(encoding="utf-8"))
        body = envelope["request"]["body"]
        routes = (envelope.get("body") or {}).get("routes") or []
        if body["origin"]["address"] not in names or not routes or body["travelMode"] != "DRIVE":
            continue
        when = datetime.fromisoformat(body["departureTime"].replace("Z", "+00:00")).astimezone(HKT)
        row = found.setdefault((names[body["origin"]["address"]], when), {})
        minutes = float(routes[0]["duration"].rstrip("s")) / 60
        row["typical" if body["trafficModel"] == "BEST_GUESS" else "upper"] = minutes
        row["free_flow"] = float(routes[0]["staticDuration"].rstrip("s")) / 60
        row["km"] = routes[0]["distanceMeters"] / 1000
    table = pd.DataFrame([{"origin": origin, "when": when, "hour": when.hour, **row}
                          for (origin, when), row in found.items() if "typical" in row and "upper" in row])
    grid_day = table["when"].dt.date.mode()[0]          # the planner's fixed road date
    return table[table["when"].dt.date == grid_day].sort_values(["origin", "hour"]).reset_index(drop=True)


def google_transit() -> pd.DataFrame:
    """One row per starting point, hour and mode (train or bus): the cached Google transit answers.

    `minutes` is the whole trip from the door (walks, waits and rides), `ride_minutes` the time on board,
    `lines` the lines used in order.
    """
    settings = get_settings()
    origins = yaml.safe_load((settings.repo_root / "data" / "reference" / "planner_origins.yaml").read_text())
    names = {o["address"]: o["name"] for o in origins["origins"]}
    rows = []
    for file in sorted((settings.data_dir / "raw" / "google").glob("*.json")):
        envelope = json.loads(file.read_text(encoding="utf-8"))
        body = envelope["request"]["body"]
        allowed = (body.get("transitPreferences") or {}).get("allowedTravelModes") or []
        seconds = google_routes.duration_seconds(envelope)
        if body.get("travelMode") != "TRANSIT" or body["origin"]["address"] not in names or not allowed or not seconds:
            continue
        when = datetime.fromisoformat(body["departureTime"].replace("Z", "+00:00")).astimezone(HKT)
        rides = google_routes.transit_lines(envelope)
        rows.append({"origin": names[body["origin"]["address"]], "mode": "train" if allowed == ["RAIL"] else "bus",
                     "hour": when.hour, "minutes": seconds / 60,
                     "ride_minutes": sum(ride["seconds"] for ride in rides) / 60,
                     "lines": ", then ".join(dict.fromkeys(ride["name"] for ride in rides if ride["name"]))})
    return pd.DataFrame(rows).sort_values(["mode", "origin", "hour"]).reset_index(drop=True)


def road_lookup(roads: pd.DataFrame, origin: str, config: dict, mode: str = "car",
                transit: pd.DataFrame | None = None):
    """A `road_for` function for the Gate Planner engine, answering from the tables (same hour of day).

    The same sums as the app's planner service (backend/app/planner.py), which research code may not import.
    """
    by_hour = roads[roads["origin"] == origin].set_index("hour")
    share = config["planner"]["fastest_share"]

    def drive(hour: int) -> Road:
        row = by_hour.loc[hour]
        return Road(row["typical"], max(row["upper"], row["typical"]), "google",
                    f"Google traffic model, Thursday {hour:02d}:00", "REAL",
                    floor=min(row["typical"], row["free_flow"]) * share)

    def lookup(when: datetime) -> Road:
        hour = min(max(when.hour, by_hour.index.min()), by_hour.index.max())
        if mode == "car":
            return drive(hour)
        trip = transit[(transit["origin"] == origin) & (transit["mode"] == mode) & (transit["hour"] == hour)].iloc[0]
        spec = config["planner"]["transit"][mode]
        upper = trip["minutes"] + spec["extra_upper"]
        if mode == "bus":
            car = drive(hour)
            upper += trip["ride_minutes"] * (car.upper / car.typical - 1)
        return Road(trip["minutes"], upper, "google_transit",
                    f"Google timetable, Thursday {hour:02d}:00: {trip['lines']}", "REAL", floor=trip["minutes"] * share)
    return lookup


def hkia_flights() -> pd.DataFrame:
    """Every stored HKIA passenger flight as a table, with the delay in minutes (None when not flown)."""
    settings = get_settings()
    files = sorted((settings.data_dir / "raw" / "hkia").glob("past_*.json"))
    rows = parse_envelopes(json.loads(file.read_text(encoding="utf-8")) for file in files)
    table = pd.DataFrame(rows)
    table["delay"] = [delay_minutes(row) for row in rows]
    table["hour"] = [row["sched"].hour for row in rows]
    return table


def zone_of(table: pd.DataFrame, zones: Zones) -> pd.Series:
    """The terminal zone of each flight: from its stand (arrivals) or its gate (departures)."""
    text = lambda value: value if isinstance(value, str) else None   # pandas stores a missing value as NaN  # noqa: E731

    def one(row) -> str:
        if row["kind"] == "arr":
            place = zones.stand(text(row["stand"]))
            return "remote stand (bus)" if place.remote else zones.name(place.zone) if place.known else "unknown"
        place = zones.gate(text(row["gate"]))
        return zones.name(place.zone) if place.known else "unknown"
    return table.apply(one, axis=1)


def estimate_errors_by_lead(flights: dict, leads=(240, 180, 120, 90, 60, 30)) -> pd.DataFrame:
    """How wrong the published in-gate estimate was, `lead` minutes before the real gate time (REAL, OAG).

    One row per arrival and lead; `error` is estimate minus actual in minutes (negative = the estimate was early).
    Only estimates published while the flight was on its way (OutGate or InAir) count.
    """
    rows = []
    for flight in flights.values():
        if flight["kind"] != "arr" or not flight["timeline"] or not flight["actual"]:
            continue
        for lead in leads:
            t = flight["actual"] - timedelta(minutes=lead)
            known = [e for e in flight["timeline"] if e["at"] <= t and e["est"] and e["state"] in ("OutGate", "InAir")]
            if known:
                rows.append({"flight": flight["flight"], "lead": lead,
                             "error": (known[-1]["est"] - flight["actual"]).total_seconds() / 60})
    return pd.DataFrame(rows)


def gate_publish_leads(flights: dict) -> pd.DataFrame:
    """Minutes before scheduled departure at which the gate first appeared in the OAG status history (REAL)."""
    rows = []
    for flight in flights.values():
        if flight["kind"] != "dep" or not flight["timeline"]:
            continue
        first = next((e for e in flight["timeline"] if e.get("gate")), None)
        if first:
            rows.append({"flight": flight["flight"], "gate": first["gate"],
                         "minutes_before": (flight["sched"] - first["at"]).total_seconds() / 60})
    return pd.DataFrame(rows)


def catch_curve(scores: np.ndarray, labels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Flag the riskiest connections first: (share flagged, share of real breaks caught), both 0..1."""
    order = np.argsort(-scores, kind="mergesort")
    caught = np.cumsum(labels[order]) / max(labels.sum(), 1)
    flagged = np.arange(1, len(scores) + 1) / len(scores)
    return np.concatenate([[0.0], flagged]), np.concatenate([[0.0], caught])
