"""The HKIA parser on rows saved from the real response for 2026-11-13 (trimmed, not edited)."""

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from flowcore.parse.hkia import delay_minutes, parse_body, parse_envelopes, parse_status

HKT = timezone(timedelta(hours=8))
FIXTURES = Path(__file__).parent / "fixtures"
DAY = date(2026, 11, 13)


def at(day: int, hour: int, minute: int) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=HKT)


@pytest.fixture(scope="module")
def envelopes():
    return {kind: json.loads((FIXTURES / f"hkia_past_2026-11-13_{kind}.json").read_text())
            for kind in ("arr", "dep")}


@pytest.fixture(scope="module")
def rows(envelopes):
    found = {}
    for kind, envelope in envelopes.items():
        for row in parse_body(envelope["body"]):
            found[(kind, row["sched_date"].isoformat(), row["flight"])] = row
    return found


@pytest.mark.parametrize("status, kind, expected", [
    ("At gate 15:10", "At gate", at(13, 15, 10)),
    ("At gate 23:32 (12/11/2026)", "At gate", at(12, 23, 32)),
    ("At gate 10:10 (14/11/2026)", "At gate", at(14, 10, 10)),
    ("Dep 13:28", "Departed", at(13, 13, 28)),
    ("Dep 00:27 (13/11/2026)", "Departed", at(13, 0, 27)),
    ("Landed 15:02", "Landed", at(13, 15, 2)),
    ("Est at 16:40", "Estimated", at(13, 16, 40)),
    ("Cancelled", "Cancelled", None),
    ("", "Other", None),
    (None, "Other", None),
    ("Gate closed", "Other", None),
])
def test_parse_status(status, kind, expected):
    assert parse_status(status, DAY) == (kind, expected)


def test_plain_arrival(rows):
    row = rows[("arr", "2026-11-13", "CX495")]
    assert row["kind"] == "arr" and row["carrier"] == "CX" and row["airline"] == "CPA"
    assert row["airport"] == "TPE" and row["codeshares"] == []
    assert row["sched"] == at(13, 15, 25) and row["actual"] == at(13, 15, 10)
    assert delay_minutes(row) == -15
    assert row["status"] == "At gate" and row["stand"] == "W61" and row["hall"] == "A"
    assert row["terminal"] is None and row["gate"] is None


def test_arrival_on_another_date_than_scheduled(rows):
    early = rows[("arr", "2026-11-13", "CX529")]  # scheduled 00:15, at gate the evening before
    assert early["actual"] == at(12, 23, 32) and delay_minutes(early) == -43
    late = rows[("arr", "2026-11-13", "CX361")]  # scheduled 11:30, at gate after midnight
    assert late["actual"] == at(14, 1, 11) and delay_minutes(late) == 13 * 60 + 41


def test_blocks_keep_their_own_scheduled_date(rows):
    row = rows[("arr", "2026-11-14", "UO685")]  # in the file for the 13th, scheduled on the 14th
    assert row["sched"] == at(14, 0, 30) and row["actual"] == at(13, 23, 53)
    row = rows[("dep", "2026-11-12", "CX173")]
    assert row["sched"] == at(12, 23, 30) and row["actual"] == at(13, 1, 3)
    assert row["airport"] == "ADL"


def test_first_flight_is_the_operator(rows):
    express = rows[("arr", "2026-11-13", "UO651")]
    assert express["carrier"] == "UO" and express["codeshares"] == ["CX5651"]
    cathay = rows[("arr", "2026-11-13", "CX636")]
    assert cathay["carrier"] == "CX" and "AY5852" in cathay["codeshares"]


def test_multi_stop_flights(rows):
    inbound = rows[("arr", "2026-11-13", "CX565")]
    assert inbound["airports"] == ["KIX", "TPE"] and inbound["airport"] == "KIX"
    outbound = rows[("dep", "2026-11-13", "CX564")]
    assert outbound["airports"] == ["TPE", "KIX"] and outbound["airport"] == "KIX"


def test_plain_departure(rows):
    row = rows[("dep", "2026-11-13", "CX253")]
    assert row["kind"] == "dep" and row["airport"] == "LHR"
    assert row["sched"] == at(13, 13, 30) and row["actual"] == at(13, 13, 28)
    assert row["status"] == "Departed" and row["gate"] == "41" and row["terminal"] == "T1"
    assert row["stand"] is None


def test_cancelled_flights_have_no_actual_time(rows):
    for key in [("arr", "2026-11-13", "HX776"), ("dep", "2026-11-13", "HX775")]:
        row = rows[key]
        assert row["cancelled"] is True and row["actual"] is None and delay_minutes(row) is None
    assert rows[("arr", "2026-11-13", "HX776")]["stand"] is None
    assert rows[("dep", "2026-11-13", "HX775")]["gate"] is None


def test_flight_number_suffix_is_kept(rows):
    assert rows[("arr", "2026-11-13", "CX270D")]["actual"] == at(14, 10, 10)


def test_envelopes_are_merged_without_duplicates(envelopes):
    arrivals = envelopes["arr"]
    # The next day's file would repeat the flights scheduled on the 14th, with a later update time.
    repeat = json.loads(json.dumps(arrivals))
    repeat["body"] = [block for block in repeat["body"] if block["date"] == "2026-11-14"]
    repeat["body"][0]["lastUpdatedTime"] = "2026-11-15T16:00:00+08:00"
    repeat["body"][0]["list"][0]["stand"] = "CHANGED"
    merged = parse_envelopes([arrivals, envelopes["dep"], repeat])
    assert len(merged) == len(parse_body(arrivals["body"])) + len(parse_body(envelopes["dep"]["body"]))
    assert [row["sched"] for row in merged] == sorted(row["sched"] for row in merged)
    assert sum(1 for row in merged if row["stand"] == "CHANGED") == 1


def test_cargo_blocks_are_skipped():
    assert parse_body([{"date": "2026-11-13", "arrival": True, "cargo": True,
                        "list": [{"time": "01:00", "flight": [{"no": "CX 3"}], "status": ""}]}]) == []
