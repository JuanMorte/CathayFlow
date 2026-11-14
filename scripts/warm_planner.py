"""Fills the road-time cache for the Gate Planner (Google Routes, through flowcore's cache and ledger).

    uv run python scripts/warm_planner.py

Every starting point × every hour 11:00–21:00 of the scenario day, mapped to the same weekday and
hour on ROAD_DATE, two traffic models each: up to 110 Google calls the first time, none after (local
and S3 cache). With the cache in place the planner works offline.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "backend")

from app.planner import google_road, origins  # noqa: E402
from flowcore.engine.time_to_gate import load_config  # noqa: E402
from flowcore.sources import google_routes  # noqa: E402

HKT = timezone(timedelta(hours=8))


def main() -> int:
    config = load_config()
    failed = 0
    for place in origins():
        row = []
        for hour in range(11, 22):
            try:
                road = google_road(place["id"], datetime(2026, 10, 22, hour, tzinfo=HKT), config)
                row.append(f"{hour}:{road.typical:.0f}/{road.upper:.0f}")
            except Exception as err:  # report and carry on; the planner falls back for this slot
                failed += 1
                row.append(f"{hour}:{type(err).__name__}")
                if isinstance(err, google_routes.KeyRejected):
                    print(f"Google rejected the key: {err}")
                    return 1
        print(f"{place['name']:14} " + "  ".join(row))
    print(f"Typical/upper minutes by hour. Failures: {failed}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
