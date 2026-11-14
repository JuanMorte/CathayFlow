"""HKIA past-flights responses → tidy flight rows (AGENTS.md §7.2).

What the real data looks like (checked on 2026-11-13, see docs/decisions.md):
- A response is a list of date blocks. The block's `date` is the **scheduled** date. A request for
  day D also returns a few flights scheduled on D−1 or D+1 whose actual time fell on D, so the same
  flight can appear in two days' files: `parse_envelopes` keeps one row per flight.
- The actual time sits inside the status string: "At gate 15:10", "Dep 13:28", and with a date when
  it is not the scheduled date: "At gate 23:32 (12/11/2026)". Past days carry "At gate", not "Landed".
- `flight[0]` is the operating flight; the rest are codeshares. `statusCode` is null.
- Arrivals list `origin` first-origin-first (["KIX", "TPE"] = KIX → TPE → HKG); departures list
  `destination` next-stop-first (["TPE", "KIX"] = HKG → TPE → KIX).
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Iterable

HKT = timezone(timedelta(hours=8))

_STATUS = re.compile(
    r"^(?P<label>[A-Za-z][A-Za-z ]*?)\s+(?P<time>\d{1,2}:\d{2})(?:\s*\((?P<date>\d{2}/\d{2}/\d{4})\))?$")
_LABELS = {
    "at gate": "At gate",
    "landed": "Landed",
    "dep": "Departed",
    "est at": "Estimated",
    "est": "Estimated",
}


def _clock(text: str) -> time:
    hour, minute = text.split(":")
    return time(int(hour), int(minute))


def parse_status(status: str | None, sched_date: date) -> tuple[str, datetime | None]:
    """`(kind, time)`; kind is At gate, Landed, Departed, Estimated, Cancelled or Other.

    A time without a date is on the scheduled date; HKIA adds "(dd/mm/yyyy)" when it is not.
    """
    text = (status or "").strip()
    if text.lower().startswith("cancel"):
        return "Cancelled", None
    match = _STATUS.match(text)
    if not match:
        return "Other", None
    kind = _LABELS.get(match["label"].strip().lower(), "Other")
    day = datetime.strptime(match["date"], "%d/%m/%Y").date() if match["date"] else sched_date
    return kind, datetime.combine(day, _clock(match["time"]), HKT)


def _flight_no(raw: str) -> str:
    return raw.replace(" ", "")


def parse_flight(item: dict, sched_date: date, arrival: bool, updated_at: str | None = None) -> dict:
    flights = item.get("flight") or [{}]
    operating = flights[0].get("no", "")
    airports = list(item.get("origin" if arrival else "destination") or [])
    kind, actual = parse_status(item.get("status"), sched_date)
    return {
        "kind": "arr" if arrival else "dep",
        "sched_date": sched_date,
        "sched": datetime.combine(sched_date, _clock(item["time"]), HKT),
        "flight": _flight_no(operating),
        "carrier": operating.split(" ")[0] if operating else "",
        "airline": flights[0].get("airline", ""),
        "codeshares": [_flight_no(f.get("no", "")) for f in flights[1:]],
        # Arrivals: where the flight started. Departures: where it ends.
        "airport": (airports[0] if arrival else airports[-1]) if airports else "",
        "airports": airports,
        "status": kind,
        "status_raw": item.get("status") or "",
        "actual": actual if kind in ("At gate", "Landed", "Departed") else None,
        "cancelled": kind == "Cancelled",
        "stand": item.get("stand") or None,
        "hall": item.get("hall") or None,
        "baggage": item.get("baggage") or None,
        "gate": item.get("gate") or None,
        "aisle": item.get("aisle") or None,
        "terminal": item.get("terminal") or None,
        "updated_at": updated_at,
    }


def parse_body(body: list[dict]) -> list[dict]:
    """Rows for every passenger flight in one response, grouped by each block's own date (§17.4.4)."""
    rows = []
    for block in body or []:
        if block.get("cargo"):
            continue
        sched_date = date.fromisoformat(block["date"])
        for item in block.get("list") or []:
            rows.append(parse_flight(item, sched_date, bool(block.get("arrival")),
                                     block.get("lastUpdatedTime")))
    return rows


def parse_envelopes(envelopes: Iterable[dict]) -> list[dict]:
    """Rows from many stored days, one per flight, sorted by scheduled time.

    A flight seen in two files keeps the row from the later `lastUpdatedTime`.
    """
    best: dict[tuple, dict] = {}
    for envelope in envelopes:
        for row in parse_body(envelope.get("body")):
            key = (row["kind"], row["sched"], row["flight"])
            seen = best.get(key)
            if seen is None or (row["updated_at"] or "") >= (seen["updated_at"] or ""):
                best[key] = row
    return sorted(best.values(), key=lambda row: (row["sched"], row["kind"], row["flight"]))


def delay_minutes(row: dict) -> float | None:
    """Actual minus scheduled, in minutes; None when there is no actual time."""
    if row["actual"] is None:
        return None
    return (row["actual"] - row["sched"]).total_seconds() / 60
