"""The demo story as a scripted scenario: Jakarta → Hong Kong → London, Tuesday 15 December 2026.

    uv run python -m flowresearch.build_story_scenario      # writes data/scenarios/2026-12-15-jakarta/

This scenario follows the product design (docs/redesign_plan.md), not a recorded day. The flight numbers
are Cathay's, but the times, the 95-minute delay, the stands and the gates are written for the story
(label SYNTHETIC); the real CX718 lands about 14:10 and the real CX251 leaves at 22:45. The engine and the
policy run on it exactly as they do on the real 22 October replay, so every risk and every held seat on
screen is computed, not typed. The delay histories and the load factor are copied from the real scenario.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

import yaml

from flowcore.config import get_settings
from flowcore.scenario import load_scenario, save_scenario

HKT = timezone(timedelta(hours=8))
SCENARIO_ID = "2026-12-15-jakarta"
REAL_SCENARIO = "2026-10-22-evening"
FLIGHT_LABELS = {name: "SYNTHETIC" for name in (
    "sched", "actual", "stand", "gate", "timeline", "dest_sched_arrival", "origin_sched_departure",
    "origin_actual_departure", "aircraft_type")} | {"cabin_seats": "ASSUMED"}


def at(hour: int, minute: int = 0, day: int = 15) -> datetime:
    return datetime(2026, 12, day, hour, minute, tzinfo=HKT)


def arrival(seats: dict) -> dict:
    """CX718 from Jakarta: planned 08:10 Jakarta time (09:10 HKT), left 95 minutes late, at the gate 15:30."""
    sched, actual = at(13, 55), at(15, 30)
    timeline = [
        {"at": at(20, 0, 14), "state": "Scheduled", "est": None, "on_ground": None},
        {"at": at(8, 30), "state": "Scheduled", "est": sched, "on_ground": None},
        {"at": at(8, 20), "state": "Scheduled", "est": at(14, 40), "on_ground": None},      # delay announced
        {"at": at(10, 45), "state": "OutGate", "est": actual, "on_ground": None},           # 09:45 in Jakarta
        {"at": at(11, 2), "state": "InAir", "est": actual, "on_ground": None},
        {"at": at(15, 21), "state": "Landed", "est": actual, "on_ground": at(15, 21)},
    ]
    return {"key": f"CX718@{sched:%Y-%m-%dT%H:%M}", "kind": "arr", "flight": "CX718", "airport": "CGK",
            "airports": ["CGK"], "city": "Jakarta", "sched": sched, "actual": actual, "cancelled": False,
            "stand": "N64", "gate": None, "terminal": None, "aircraft_type": "333", "cabin_seats": seats,
            "origin_sched_departure": "2026-12-15T08:10", "origin_actual_departure": "2026-12-15T09:45",
            "origin_terminal": "Terminal 3", "dest_sched_arrival": None, "wave_load": 1.0,
            "timeline": timeline, "labels": dict(FLIGHT_LABELS)}


def departure(flight: str, airport: str, city: str, sched: datetime, gate: str, dest_arrival: str,
              seats: dict, dest_terminal: str | None = None) -> dict:
    published = sched - timedelta(hours=11)             # story: gates known by the time an agent rebooks
    timeline = [
        {"at": sched - timedelta(days=1), "state": "Scheduled", "est": None, "on_ground": None, "gate": None},
        {"at": sched - timedelta(hours=8), "state": "Scheduled", "est": sched, "on_ground": None, "gate": None},
        {"at": published, "state": "Scheduled", "est": sched, "on_ground": None, "gate": gate},
    ]
    return {"key": f"{flight}@{sched:%Y-%m-%dT%H:%M}", "kind": "dep", "flight": flight, "airport": airport,
            "airports": [airport], "city": city, "sched": sched, "actual": sched, "cancelled": False,
            "stand": None, "gate": gate, "terminal": "T1", "aircraft_type": "333", "cabin_seats": seats,
            "origin_sched_departure": None, "dest_sched_arrival": dest_arrival, "dest_terminal": dest_terminal,
            "timeline": timeline, "labels": dict(FLIGHT_LABELS)}


def party(party_id: str, members: list[dict], cabin: str, seat: str, alt_seat: str, row_frac: float, tier: str,
          outbound: dict, inbound: dict, *, assistance: str | None = None, bags: int = 1) -> dict:
    return {"party_id": party_id, "size": len(members), "cabin": cabin, "seat": seat, "alt_seat": alt_seat,
            "assistance_note": assistance,
            "row_frac": row_frac, "tier": tier, "assistance": assistance is not None, "bags": bags,
            "preference": "earliest_arrival", "members": members, "is_synthetic": True,
            "inbound": inbound["key"], "outbound": outbound["key"],
            "sched_gap_min": int((outbound["sched"] - inbound["sched"]).total_seconds() // 60)}


def build() -> tuple[dict, list[dict], list[dict]]:
    root = get_settings().repo_root
    real = load_scenario(REAL_SCENARIO)["meta"]
    types = yaml.safe_load((root / "data" / "reference" / "aircraft_seats.yaml").read_text())["types"]
    seats = {cabin: types["333"][cabin] for cabin in ("F", "J", "W", "Y")}

    inbound = arrival(seats)
    london = departure("CX251", "LHR", "London", at(16, 5), "6", "2026-12-15T22:05", seats, "Terminal 3")
    los_angeles = departure("CX880", "LAX", "Los Angeles", at(16, 15), "30", "2026-12-15T12:40", seats)
    sydney = departure("CX101", "SYD", "Sydney", at(16, 30), "210", "2026-12-16T05:00", seats)
    tokyo = departure("CX504", "NRT", "Tokyo", at(16, 0), "28", "2026-12-15T21:10", seats)
    later = [
        departure("CX500", "NRT", "Tokyo", at(18, 40), "25", "2026-12-15T23:50", seats),
        departure("CX884", "LAX", "Los Angeles", at(23, 35), "32", "2026-12-15T20:00", seats),
        departure("CX139", "SYD", "Sydney", at(23, 40), "4", "2026-12-16T12:10", seats),
        departure("CX255", "LHR", "London", at(23, 55), "23", "2026-12-16T05:55", seats, "Terminal 3"),
    ]
    parties = [
        party("WIJAYA", [{"pid": "WIJAYA-1", "name": "Eka Wijaya", "title": "Ms"},
                         {"pid": "WIJAYA-2", "name": "Kai Wijaya"}],
              "J", "11A", "14A", 0.27, "Gold", london, inbound, bags=2),
        party("CHAN", [{"pid": "CHAN-1", "name": "Ming Chan"}], "Y", "34C", "34C", 0.5, "Green",
              los_angeles, inbound, assistance="Wheelchair assistance"),
        party("NGUYEN", [{"pid": "NGUYEN-1", "name": "Thao Nguyen"}], "Y", "62C", "42C", 1.0, "Green",
              sydney, inbound),
        party("KIM", [{"pid": "KIM-1", "name": "Jisoo Kim"}], "J", "12K", "1A", 0.3, "Diamond", tokyo, inbound),
        party("OKAFOR", [{"pid": "OKAFOR-1", "name": "Tunde Okafor"}], "Y", "30D", "30D", 0.0, "Green",
              london, inbound),
    ]
    meta = {
        "id": SCENARIO_ID, "title": "Tuesday 15 December 2026, Jakarta to London via Hong Kong (demo story)",
        "day": "2026-12-15", "default": True, "illustrative": True,
        # From the evening before (Jakarta 21:30) until she is out of Heathrow (London 07:30).
        "replay_start": at(22, 30, 14), "replay_end": at(15, 30, 16), "hero_pid": "WIJAYA-1", "seed": 20261215,
        # Other agents on shift decide some rows before the demo reaches the console (13:46).
        "scripted_decisions": [
            {"at": "2026-12-15T13:40:00+08:00", "party_id": "NGUYEN", "decision": "approve"},
            {"at": "2026-12-15T13:42:00+08:00", "party_id": "KIM", "decision": "approve"},
            {"at": "2026-12-15T13:44:00+08:00", "party_id": "OKAFOR", "decision": "reject",
             "note": "Fast-transfer route"},
        ],
        "history_window": real["history_window"],
        "inbound_delay_quantiles": real["inbound_delay_quantiles"],
        "outbound_delay_quantiles": real["outbound_delay_quantiles"],
        "busy_wave_arrivals": real["busy_wave_arrivals"], "load_factor": real["load_factor"],
        "labels": {"flights": "SYNTHETIC", "timelines": "SYNTHETIC", "passengers": "SYNTHETIC",
                   "inbound_delay_quantiles": "REAL", "outbound_delay_quantiles": "REAL", "load_factor": "REAL",
                   "cabin_seats": "ASSUMED"},
        "sources": {"flights": "Written for the demo story (docs/redesign_plan.md); not a recorded day",
                    "history": f"Copied from the real scenario {REAL_SCENARIO}",
                    "load_factor": real["sources"]["load_factor"]},
    }
    return meta, [inbound, london, los_angeles, sydney, tokyo, *later], parties


README = """# 2026-12-15-jakarta: the demo story

Jakarta → Hong Kong → London on Tuesday 15 December 2026, as drawn in the product design.

**This is a scripted scenario, not a recorded day.** The flight numbers are Cathay's; the times, the
95-minute delay, the stands and the gates were written for the story. The real CX718 lands about 14:10 and
the real CX251 leaves at 22:45. Everything computed on screen (miss risk, held seats, who is rebooked) comes
from the same engine and policy as the real replay in `../2026-10-22-evening/`, which is the one to cite as
evidence. The delay histories and the load factor are copied from that real scenario.

Rebuild: `uv run python -m flowresearch.build_story_scenario`.
"""


def main() -> int:
    meta, flights, parties = build()
    folder = save_scenario(meta, flights, parties)
    (folder / "README.md").write_text(README, encoding="utf-8")
    print(f"Wrote {folder}: {len(flights)} flights, {len(parties)} parties.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
