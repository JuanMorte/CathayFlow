"""OAG Flight Info and Connections (AGENTS.md §7.3).

1,000 calls per 30 days per account, shared by both products, 10 results per call. Query
specific flights, never whole days (§17.4.2). Raw responses stay in S3 and out of git.
"""

from __future__ import annotations

import re
import time

import httpx

from flowcore import aws
from flowcore.cache import Cache, Ledger, SourceError, cache_key, make_request
from flowcore.config import Settings, get_settings
from flowcore.sources import MissingKey, http_client, parse

FLIGHT_INFO_URL = "https://api.oag.com/flight-instances/"
VERSION = "v2"
# OAG also limits calls per minute (HTTP 429 "Try again in N seconds"): wait and retry.
RATE_LIMIT_RETRIES = 3


def _key(product: str, settings: Settings) -> str | None:
    profile = settings.oag_key_profile
    if product == "flight-info":
        return aws.get_secret(f"oag-key-{profile}", f"OAG_KEY_{profile.upper()}", settings)
    return aws.get_secret(f"oag-connections-key-{profile}",
                          f"OAG_CONNECTIONS_KEY_{profile.upper()}", settings)


def _check_params(params: dict) -> None:
    if not ({"DepartureDateTime", "ArrivalDateTime"} & params.keys()):
        raise ValueError("OAG needs DepartureDateTime or ArrivalDateTime.")
    if not ({"CarrierCode", "DepartureAirport", "ArrivalAirport"} & params.keys()):
        raise ValueError("OAG needs CarrierCode, DepartureAirport or ArrivalAirport.")


def _get(url: str, params: dict, product: str, cache: Cache | None,
         http: httpx.Client | None, settings: Settings | None) -> dict:
    s = settings or get_settings()
    cache = cache or Cache(s)
    request = make_request("oag", url, params)
    state: dict = {}

    def ledger() -> Ledger:
        # Both products count against the account, identified by its Flight Info key.
        account_key = _key("flight-info", s) or state["key"]
        return Ledger("oag", account_key, s.oag_max_calls, s)

    def call():
        owned = http is None
        session = http or http_client()
        try:
            # `params={}` would make httpx drop the query string of a next-page URL.
            return parse(session.get(url, params=params or None,
                                     headers={"Subscription-Key": state["key"]}))
        finally:
            if owned:
                session.close()

    # A cached answer needs no key, so look before asking SSM for one.
    hit = cache.get("oag", cache_key(request))
    if hit is not None:
        return hit
    if s.offline:
        return cache.fetch(request, call)  # raises OfflineCacheMiss naming the request
    key = _key(product, s)
    if not key:
        raise MissingKey(f"No OAG {product} key for profile '{s.oag_key_profile}' (see `make secrets`).")
    state["key"] = key
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        try:
            return cache.fetch(request, call, ledger=ledger())
        except SourceError as err:
            if err.status != 429 or attempt == RATE_LIMIT_RETRIES:
                raise
            wait = re.search(r"(\d+) seconds", str(err.body))
            time.sleep(min(int(wait[1]) + 2 if wait else 60, 90))
        except httpx.TimeoutException:
            if attempt == RATE_LIMIT_RETRIES:
                raise
            time.sleep(5)


def flight_instances(params: dict, *, cache: Cache | None = None, http: httpx.Client | None = None,
                     settings: Settings | None = None) -> dict:
    """One page (≤ 10 records) of Flight Info. `Content`: blank, STATUS, STATUSDETAILED or SEATS."""
    _check_params(params)
    # CodeType is required whenever a carrier or airport is given (HTTP 400 without it).
    return _get(FLIGHT_INFO_URL, {"version": VERSION, "CodeType": "IATA", **params}, "flight-info",
                cache, http, settings)


def next_page(envelope: dict, *, cache: Cache | None = None, http: httpx.Client | None = None,
              settings: Settings | None = None) -> dict | None:
    """Follow `paging.next` (a full URL with an `After=` cursor). Each page is one more call."""
    url = ((envelope.get("body") or {}).get("paging") or {}).get("next")
    if not url:
        return None
    return _get(url, {}, "flight-info", cache, http, settings)


def connections(params: dict, *, cache: Cache | None = None, http: httpx.Client | None = None,
                settings: Settings | None = None) -> dict:
    """OAG Connections. The URL comes from the portal's "Try it" page (OAG_CONNECTIONS_URL)."""
    s = settings or get_settings()
    if not s.oag_connections_url:
        raise ValueError("OAG_CONNECTIONS_URL is not set; copy it from the OAG portal.")
    return _get(s.oag_connections_url, params, "connections", cache, http, s)


def calls_used(settings: Settings | None = None) -> int | None:
    """Live calls in the last 30 days for the current key profile; None without a key."""
    s = settings or get_settings()
    key = _key("flight-info", s)
    return Ledger("oag", key, s.oag_max_calls, s).count() if key else None
