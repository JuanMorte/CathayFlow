"""Scenario files: read and write (data/scenarios/<id>/, AGENTS.md §6).

A scenario is three JSON files plus a README:
- scenario.json: id, title, replay window, hero, history statistics (REAL history, derived).
- flights.json: Cathay-operated flights at HKG with their published-estimate timelines (REAL).
- passengers.json: synthetic parties and their connections (SYNTHETIC).

JSON, not Parquet: the files are small, readable in a diff, and keep heavy libraries out of the
app image (docs/decisions.md).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from flowcore.config import find_repo_root

FLIGHT_TIMES = ("sched", "actual")
EVENT_TIMES = ("at", "est", "on_ground")
SCENARIO_TIMES = ("replay_start", "replay_end")


def scenarios_dir() -> Path:
    return find_repo_root() / "data" / "scenarios"


def _parse(value):
    return datetime.fromisoformat(value) if isinstance(value, str) else value


def _dump(value):
    return value.isoformat() if isinstance(value, datetime) else value


def list_scenarios() -> list[dict]:
    found = []
    for file in sorted(scenarios_dir().glob("*/scenario.json")):
        meta = json.loads(file.read_text(encoding="utf-8"))
        found.append({"id": meta["id"], "title": meta["title"]})
    return found


def save_scenario(meta: dict, flights: list[dict], parties: list[dict]) -> Path:
    folder = scenarios_dir() / meta["id"]
    folder.mkdir(parents=True, exist_ok=True)
    out_meta = {**meta, **{name: _dump(meta[name]) for name in SCENARIO_TIMES}}
    out_flights = []
    for flight in flights:
        row = {**flight, **{name: _dump(flight.get(name)) for name in FLIGHT_TIMES}}
        row["timeline"] = [{**event, **{name: _dump(event.get(name)) for name in EVENT_TIMES}}
                           for event in flight.get("timeline") or []]
        out_flights.append(row)
    for name, payload in (("scenario.json", out_meta), ("flights.json", out_flights),
                          ("passengers.json", parties)):
        (folder / name).write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                                   encoding="utf-8")
    return folder


def load_scenario(scenario_id: str) -> dict:
    """`{meta, flights: {key: flight}, parties: [...]}` with every time parsed."""
    folder = scenarios_dir() / scenario_id
    meta = json.loads((folder / "scenario.json").read_text(encoding="utf-8"))
    for name in SCENARIO_TIMES:
        meta[name] = _parse(meta[name])
    flights = {}
    for flight in json.loads((folder / "flights.json").read_text(encoding="utf-8")):
        for name in FLIGHT_TIMES:
            flight[name] = _parse(flight.get(name))
        for event in flight.get("timeline") or []:
            for name in EVENT_TIMES:
                event[name] = _parse(event.get(name))
        flights[flight["key"]] = flight
    parties = json.loads((folder / "passengers.json").read_text(encoding="utf-8"))
    return {"meta": meta, "flights": flights, "parties": parties}
