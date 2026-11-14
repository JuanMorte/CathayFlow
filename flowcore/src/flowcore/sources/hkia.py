"""HKIA past flights: whole days, with stands and gates. Free, no key (AGENTS.md §7.2).

The window is exactly 91 days back from yesterday; older dates answer HTTP 400 (§17.4.4).
"""

from __future__ import annotations

from datetime import date

import httpx

from flowcore.cache import Cache, make_request
from flowcore.sources import http_client, parse

URL = "https://www.hongkongairport.com/flightinfo-rest/rest/flights/past"
WINDOW_DAYS = 91


def past_key(day: date, arrival: bool) -> str:
    return f"past_{day.isoformat()}_{'arr' if arrival else 'dep'}"


def past_params(day: date, arrival: bool) -> dict[str, str]:
    return {"date": day.isoformat(), "lang": "en", "cargo": "false",
            "arrival": "true" if arrival else "false"}


def fetch_past(day: date, arrival: bool, *, cache: Cache | None = None,
               http: httpx.Client | None = None) -> dict:
    """The stored envelope for one day of passenger arrivals or departures."""
    cache = cache or Cache()
    params = past_params(day, arrival)

    def call():
        owned = http is None
        session = http or http_client()
        try:
            return parse(session.get(URL, params=params))
        finally:
            if owned:
                session.close()

    # An empty body is returned but not stored, so the day is retried later.
    return cache.fetch(make_request("hkia", URL, params), call,
                       key=past_key(day, arrival), keep=bool)
