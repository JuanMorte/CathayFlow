"""Builds data/scenarios/<id>/ from stored HKIA days and OAG status histories.

    make data-down                                   # HKIA days from S3 to data/raw/hkia
    uv run python -m flowresearch.build_scenario     # about 47 OAG calls the first time, then cached

Flights, times, stands and gates are REAL (HKIA). Estimate timelines are REAL (OAG, as published).
Passengers are SYNTHETIC (seeded). Raw OAG responses stay in data/raw and S3; only the derived
timelines are written to the scenario folder (AGENTS.md §17.4.3).
"""

from __future__ import annotations

import bisect
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import numpy as np
import yaml

from flowcore.cache import SourceError
from flowcore.config import get_settings
from flowcore.parse.hkia import delay_minutes, parse_envelopes
from flowcore.scenario import save_scenario
from flowcore.sources import oag
from flowresearch import synth

HKT = timezone(timedelta(hours=8))

SCENARIO = {
    "id": "2026-10-22-evening",
    "title": "Thursday 22 October 2026, evening wave at Hong Kong",
    "day": "2026-10-22",
    # 05:30 so CX254's late pushback in London (published 05:37) happens on screen.
    "replay_start": "05:30",
    "replay_end": "20:30",
    "inbound_window": ("16:45", "19:30"),     # scheduled arrivals whose passengers we follow
    "outbound_until": "23:30",                # latest scheduled connecting departure
    "oag_outbound_until": "20:10",            # status histories are pulled for departures up to here
    "alternatives_until_hours": 20,           # later flights kept as rebooking alternatives
    "history_from": "2026-08-15",             # pinned window for history statistics (§17.4.6)
    "seed": 20261022,
    # REAL: Cathay Pacific passenger load factor, August 2026 (latest monthly release before the
    # scenario day; Cathay Group traffic figures).
    "load_factor": 0.872,
    # REAL, derived: transfer and transit passengers 1.50 M of 5.37 M at HKIA, October 2025 (AAHK).
    # Airport-wide, all airlines; used as Cathay's share connecting onward within four hours.
    "transfer_share": 0.28,
    "hero": {"inbound": "CX254", "outbound": "CX135", "name": "Mei Chen", "cabin": "J",
             "seat": "15A", "row_frac": 0.27, "tier": "Gold", "preference": "earliest_arrival"},
}


def at(day: date, clock: str, plus_days: int = 0) -> datetime:
    hour, minute = clock.split(":")
    return datetime(day.year, day.month, day.day, int(hour), int(minute), tzinfo=HKT) + timedelta(days=plus_days)


def load_rows(settings) -> list[dict]:
    files = sorted((settings.data_dir / "raw" / "hkia").glob("past_*.json"))
    if not files:
        raise SystemExit("No HKIA days in data/raw/hkia. Run `make data-down` first.")
    return parse_envelopes(json.loads(file.read_text(encoding="utf-8")) for file in files)


def flight_key(row: dict) -> str:
    return f"{row['flight']}@{row['sched']:%Y-%m-%dT%H:%M}"


def utc_to_hkt(stamp: str) -> datetime:
    """OAG `updatedAt` is UTC without an offset."""
    return datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc).astimezone(HKT)


def local_time(node: dict | None, *path: str) -> datetime | None:
    for name in path:
        node = (node or {}).get(name)
    value = (node or {}).get("local") if isinstance(node, dict) else None
    return datetime.fromisoformat(value).astimezone(HKT) if value else None


def schedule_types(day: date, until: datetime) -> dict[tuple[str, str], str]:
    """Aircraft type of every Cathay departure from HKG on `day` up to `until` (OAG schedules,
    10 per page, pages stop once past `until`). Key: (flight, scheduled local time)."""
    found: dict[tuple[str, str], str] = {}
    envelope = oag.flight_instances({"DepartureAirport": "HKG", "CarrierCode": "CX",
                                     "DepartureDateTime": day.isoformat()})
    while envelope:
        records = envelope["body"].get("data") or []
        for record in records:
            if (record.get("carrier") or {}).get("iata") != "CX":
                continue
            when = f"{record['departure']['date']['local']}T{record['departure']['time']['local']}"
            kind = (record.get("aircraftType") or {}).get("iata")
            if kind:
                found[(f"CX{record['flightNumber']}", when)] = kind
        last = records[-1]["departure"] if records else None
        if not last or datetime.fromisoformat(f"{last['date']['local']}T{last['time']['local']}").replace(
                tzinfo=HKT) > until:
            break
        envelope = oag.next_page(envelope)
    return found


def oag_timeline(row: dict) -> tuple[list[dict], str | None, str | None]:
    """Published estimates for one flight, oldest first, each with the time it became known;
    for departures the scheduled arrival at the destination (local time there); and the
    aircraft type."""
    number = re.fullmatch(r"CX(\d+)", row["flight"])
    if not number or row["cancelled"]:
        return [], None, None
    arrival = row["kind"] == "arr"
    params = {"CarrierCode": "CX", "FlightNumber": number[1], "Content": "STATUSDETAILED",
              ("ArrivalDateTime" if arrival else "DepartureDateTime"): row["sched"].date().isoformat()}
    try:
        body = oag.flight_instances(params)["body"]
    except SourceError as err:
        print(f"  OAG {row['flight']}: {err}", file=sys.stderr)
        return [], None, None
    side = "arrival" if arrival else "departure"
    records = [record for record in body.get("data") or []
               if record.get("statusDetails") and (record.get(side, {}).get("airport") or {}).get("iata") == "HKG"]
    if not records:
        return [], None, None
    aircraft = (records[0].get("aircraftType") or {}).get("iata")
    # The far end's scheduled time, local there: the destination arrival for a departure, the
    # origin departure for an arrival.
    far = records[0].get("departure" if arrival else "arrival") or {}
    day_local, clock_local = (far.get("date") or {}).get("local"), (far.get("time") or {}).get("local")
    dest_arrival = f"{day_local}T{clock_local}" if day_local and clock_local else None
    events = []
    for update in sorted(records[0]["statusDetails"], key=lambda u: u.get("updatedAt") or ""):
        if not update.get("updatedAt"):
            continue
        if arrival:
            actual_gate = local_time(update, "arrival", "actualTime", "inGate")
            event = {"at": utc_to_hkt(update["updatedAt"]), "state": update.get("state"),
                     "est": actual_gate or local_time(update, "arrival", "estimatedTime", "inGate"),
                     "on_ground": local_time(update, "arrival", "actualTime", "onGround")}
        else:
            actual_out = local_time(update, "departure", "actualTime", "outGate")
            event = {"at": utc_to_hkt(update["updatedAt"]), "state": update.get("state"),
                     "est": actual_out or local_time(update, "departure", "estimatedTime", "outGate"),
                     "on_ground": None,
                     # The departure gate as published at this moment (REAL); gate changes show up here.
                     "gate": (update.get("departure") or {}).get("gate")}
        if not events or any(events[-1].get(name) != event.get(name) for name in ("state", "est", "on_ground", "gate")):
            events.append(event)
    return events, dest_arrival, aircraft


def wave_counts(rows: list[dict]) -> dict:
    """Scheduled passenger arrivals (all airlines) per day, as sorted minute-of-day lists."""
    per_day = defaultdict(list)
    for row in rows:
        if row["kind"] == "arr" and not row["cancelled"]:
            per_day[row["sched_date"]].append(row["sched"].hour * 60 + row["sched"].minute)
    return {day: sorted(minutes) for day, minutes in per_day.items()}


def arrivals_within(minutes: list[int], centre: int, half_window: int = 30) -> int:
    return bisect.bisect_right(minutes, centre + half_window) - bisect.bisect_left(minutes, centre - half_window)


def build() -> int:
    settings = get_settings()
    spec = SCENARIO
    day = date.fromisoformat(spec["day"])
    history_from = date.fromisoformat(spec["history_from"])
    rows = load_rows(settings)
    airports_file = yaml.safe_load((settings.repo_root / "data" / "reference" / "airports.yaml").read_text())
    airports, implausible = airports_file["airports"], airports_file["implausible_pairs"]

    cathay = [row for row in rows if row["carrier"] == "CX"]
    history = [row for row in cathay if history_from <= row["sched_date"] < day]

    # History statistics, from days strictly before the scenario day (no leakage).
    arrival_delays = sorted(delay_minutes(row) for row in history
                            if row["kind"] == "arr" and row["actual"] and not row["cancelled"])
    inbound_delay_quantiles = [round(float(q), 1) for q in np.quantile(arrival_delays, np.linspace(0, 1, 41))]
    # A late departure moves gate close later; an early one does not move it earlier.
    departure_delays = [max(delay_minutes(row), 0.0) for row in history
                        if row["kind"] == "dep" and row["actual"] and not row["cancelled"]]
    outbound_delay_quantiles = [round(float(q), 1) for q in np.quantile(departure_delays, np.linspace(0, 1, 41))]
    waves = wave_counts(rows)
    history_counts = [arrivals_within(waves[d], minute) for d in waves if history_from <= d < day
                      for minute in waves[d]]
    busy = float(np.quantile(history_counts, 0.95))

    low, high = (at(day, clock) for clock in spec["inbound_window"])
    inbound_rows = [row for row in cathay if row["kind"] == "arr" and low <= row["sched"] <= high]
    out_low = low + timedelta(minutes=50)
    connect_until = at(day, spec["outbound_until"])
    keep_until = connect_until + timedelta(hours=spec["alternatives_until_hours"])
    outbound_rows = [row for row in cathay if row["kind"] == "dep" and out_low <= row["sched"] <= keep_until]
    oag_until = at(day, spec["oag_outbound_until"])
    hero_outbound = next(row for row in outbound_rows if row["flight"] == spec["hero"]["outbound"])
    hero_destination = hero_outbound["airport"]
    hero_alternatives_until = hero_outbound["sched"] + timedelta(hours=spec["alternatives_until_hours"])

    flights = []
    for row in inbound_rows + outbound_rows:
        # Status histories for every inbound, the early departures, and the hero's alternatives.
        wants_oag = (row["kind"] == "arr" or row["sched"] <= oag_until
                     or (row["airport"] == hero_destination and row["sched"] <= hero_alternatives_until))
        timeline, dest_arrival, aircraft = oag_timeline(row) if wants_oag else ([], None, None)
        flight = {
            "key": flight_key(row), "kind": row["kind"], "flight": row["flight"],
            "airport": row["airport"], "airports": row["airports"],
            "city": airports.get(row["airport"], {}).get("city", row["airport"]),
            "sched": row["sched"], "actual": row["actual"], "cancelled": row["cancelled"],
            "stand": row["stand"], "gate": row["gate"], "terminal": row["terminal"],
            "timeline": timeline,
            "aircraft_type": aircraft,
            # Scheduled arrival at the destination, local time there (departures with an OAG record).
            "dest_sched_arrival": dest_arrival if row["kind"] == "dep" else None,
            # Scheduled departure from the origin, local time there (arrivals with an OAG record).
            "origin_sched_departure": dest_arrival if row["kind"] == "arr" else None,
            "labels": {"sched": "REAL", "actual": "REAL", "stand": "REAL", "gate": "REAL",
                       "timeline": "REAL", "dest_sched_arrival": "REAL", "origin_sched_departure": "REAL"},
        }
        if row["kind"] == "arr":
            count = arrivals_within(waves[row["sched_date"]], row["sched"].hour * 60 + row["sched"].minute)
            flight["wave_arrivals"] = count
            flight["wave_load"] = round(min(count / busy, 1.0), 3)
        flights.append(flight)
    with_timeline = sum(1 for flight in flights if flight["timeline"])

    # Aircraft type for departures without a status history: one schedule query per day.
    types = {}
    for offset in range(2):
        types.update(schedule_types(day + timedelta(days=offset), keep_until))
    seat_table = yaml.safe_load((settings.repo_root / "data" / "reference" / "aircraft_seats.yaml").read_text())
    for flight in flights:
        if not flight["aircraft_type"]:
            flight["aircraft_type"] = types.get((flight["flight"], f"{flight['sched']:%Y-%m-%dT%H:%M}"))
        flight["cabin_seats"] = synth.cabin_layout(flight, seat_table)
        flight["labels"].update(aircraft_type="REAL", cabin_seats="ASSUMED")
    typed = sum(1 for flight in flights if flight["aircraft_type"])

    by_key = {flight["key"]: flight for flight in flights}
    connecting_out = [flight for flight in flights if flight["kind"] == "dep" and flight["sched"] <= connect_until]
    parties, per_arrival = synth.make_connections(
        [flight for flight in flights if flight["kind"] == "arr" and not flight["cancelled"]],
        connecting_out, airports, implausible, seat_table, spec["load_factor"],
        spec["transfer_share"], spec["seed"])

    hero = spec["hero"]
    hero_in = next(f for f in flights if f["kind"] == "arr" and f["flight"] == hero["inbound"])
    hero_out = next(f for f in connecting_out if f["flight"] == hero["outbound"])
    parties.insert(0, {
        "party_id": "MEI", "size": 1, "cabin": hero["cabin"], "seat": hero["seat"],
        "row_frac": hero["row_frac"], "tier": hero["tier"], "assistance": False,
        "preference": hero["preference"], "members": [{"pid": "MEI-1", "name": hero["name"]}],
        "is_synthetic": True, "inbound": hero_in["key"], "outbound": hero_out["key"],
        "sched_gap_min": int((hero_out["sched"] - hero_in["sched"]).total_seconds() / 60),
    })
    assert all(party["inbound"] in by_key and party["outbound"] in by_key for party in parties)

    meta = {
        "id": spec["id"], "title": spec["title"], "day": spec["day"],
        "replay_start": at(day, spec["replay_start"]), "replay_end": at(day, spec["replay_end"]),
        "hero_pid": "MEI-1", "seed": spec["seed"],
        "history_window": [spec["history_from"], (day - timedelta(days=1)).isoformat()],
        "inbound_delay_quantiles": inbound_delay_quantiles,
        "outbound_delay_quantiles": outbound_delay_quantiles,
        "busy_wave_arrivals": busy,
        "load_factor": spec["load_factor"],
        "transfer_share": spec["transfer_share"],
        "connections_per_arrival": per_arrival,
        "labels": {"flights": "REAL", "timelines": "REAL", "passengers": "SYNTHETIC",
                   "inbound_delay_quantiles": "REAL", "outbound_delay_quantiles": "REAL",
                   "busy_wave_arrivals": "REAL",
                   "aircraft_type": "REAL", "cabin_seats": "ASSUMED", "load_factor": "REAL",
                   "transfer_share": "REAL", "connections_per_arrival": "SYNTHETIC"},
        "sources": {"flights": "HKIA past flights", "timelines": "OAG Flight Info, STATUSDETAILED",
                    "aircraft_type": "OAG Flight Info", "cabin_seats": "data/reference/aircraft_seats.yaml",
                    "load_factor": "Cathay Group traffic figures, August 2026",
                    "transfer_share": "AAHK air traffic figures, October 2025 (1.50 M of 5.37 M)"},
    }
    folder = save_scenario(meta, flights, parties)
    passengers = sum(party["size"] for party in parties)
    tight = sum(party["size"] for party in parties if party["sched_gap_min"] <= 89)
    print(f"Wrote {folder.relative_to(settings.repo_root)}: {len(inbound_rows)} inbound and "
          f"{len(outbound_rows)} outbound flights ({with_timeline} with OAG timelines), "
          f"{len(parties)} parties, {passengers} passengers ({tight} on a 50 to 89 minute connection).")
    print(f"Aircraft type known for {typed} of {len(flights)} flights.")
    for row in per_arrival:
        print(f"  {row['flight']:7} {row['from']} {row['aircraft_type'] or '?':4} {row['seats']:4} seats -> "
              f"{row['connecting']:3} connecting over {row['onward_flights']} onward flights")
    print(f"History: {len(arrival_delays)} Cathay arrivals; busy half-hour = {busy:.0f} arrivals within 30 minutes.")
    print(f"OAG live calls in the last 30 days: {oag.calls_used(settings)} of {settings.oag_max_calls}.")
    return 0


if __name__ == "__main__":
    sys.exit(build())
