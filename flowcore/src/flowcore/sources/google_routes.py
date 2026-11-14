"""Google Routes for the Gate Planner road leg (AGENTS.md §7.4).

Traffic needs a future departure time (§17.4.5). After one key rejection this process stops
calling Google, which protects the ledger; the planner then uses the Airport Express table.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from flowcore import aws
from flowcore.cache import Cache, Ledger, SourceError, cache_key, make_request
from flowcore.config import Settings, get_settings
from flowcore.sources import MissingKey, http_client, parse

URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
FIELD_MASK = "routes.duration,routes.staticDuration,routes.distanceMeters"
# Transit replies also say which lines the route uses, so the planner can name them.
TRANSIT_FIELD_MASK = ("routes.duration,routes.distanceMeters,routes.legs.steps.travelMode,"
                      "routes.legs.steps.staticDuration,routes.legs.steps.transitDetails.transitLine.name,"
                      "routes.legs.steps.transitDetails.transitLine.nameShort,"
                      "routes.legs.steps.transitDetails.transitLine.vehicle.type")
AIRPORT = "Hong Kong International Airport Terminal 1"
ROUND_MINUTES = 15

_key_rejected = False


class KeyRejected(RuntimeError):
    """Google refused the key; no more live calls in this process."""


def reset_key_rejected() -> None:
    global _key_rejected
    _key_rejected = False


def round_departure(when: datetime) -> datetime:
    """Floor to 15 minutes so nearby requests share one cache entry."""
    if when.tzinfo is None:
        raise ValueError("departure_time must be timezone-aware.")
    when = when.astimezone(timezone.utc)
    return when.replace(minute=when.minute - when.minute % ROUND_MINUTES, second=0, microsecond=0)


def build_body(origin: str, destination: str, departure_time: datetime, travel_mode: str,
               traffic_model: str | None, transit_modes: tuple[str, ...] | None = None) -> dict:
    body = {
        "origin": {"address": origin},
        "destination": {"address": destination},
        "travelMode": travel_mode,
        "departureTime": round_departure(departure_time).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if travel_mode == "DRIVE":
        body["routingPreference"] = "TRAFFIC_AWARE_OPTIMAL"
        body["trafficModel"] = traffic_model or "BEST_GUESS"
    if travel_mode == "TRANSIT" and transit_modes:
        body["transitPreferences"] = {"allowedTravelModes": list(transit_modes)}
    return body


def compute_route(origin: str, departure_time: datetime, *, destination: str = AIRPORT,
                  travel_mode: str = "DRIVE", traffic_model: str | None = None,
                  transit_modes: tuple[str, ...] | None = None,
                  cache: Cache | None = None, http: httpx.Client | None = None,
                  settings: Settings | None = None) -> dict:
    """The stored envelope. `traffic_model`: PESSIMISTIC (upper) or BEST_GUESS (typical); DRIVE only.
    `transit_modes`: TRANSIT only, e.g. ("RAIL",) or ("BUS",); Google then uses only those vehicles."""
    global _key_rejected
    s = settings or get_settings()
    cache = cache or Cache(s)
    body = build_body(origin, destination, departure_time, travel_mode, traffic_model, transit_modes)
    field_mask = TRANSIT_FIELD_MASK if travel_mode == "TRANSIT" else FIELD_MASK
    request = make_request("google", URL, body=body)
    state: dict = {}

    def call():
        owned = http is None
        session = http or http_client()
        try:
            return parse(session.post(URL, json=body, headers={
                "X-Goog-Api-Key": state["key"], "X-Goog-FieldMask": field_mask}))
        finally:
            if owned:
                session.close()

    hit = cache.get("google", cache_key(request))
    if hit is not None:
        return hit
    if s.offline:
        return cache.fetch(request, call)  # raises OfflineCacheMiss naming the request
    if _key_rejected:
        raise KeyRejected("Google rejected the key earlier in this process.")
    key = aws.get_secret("google-routes-key", "GOOGLE_ROUTES_KEY", s)
    if not key:
        raise MissingKey("No Google Routes key (see `make secrets`).")
    state["key"] = key
    try:
        return cache.fetch(request, call, ledger=Ledger("google", key, s.google_max_calls, s))
    except SourceError as err:
        if err.status in (401, 403) or (err.status == 400 and "API key" in str(err)):
            _key_rejected = True
            raise KeyRejected(str(err)) from err
        raise


def transit_lines(envelope: dict) -> list[dict]:
    """The transit rides of the first route, in order: `{"name", "vehicle", "seconds"}`."""
    routes = (envelope.get("body") or {}).get("routes") or []
    rides = []
    for leg in (routes[0].get("legs") or []) if routes else []:
        for step in leg.get("steps") or []:
            line = (step.get("transitDetails") or {}).get("transitLine")
            if line:
                rides.append({"name": line.get("nameShort") or line.get("name") or "",
                              "vehicle": (line.get("vehicle") or {}).get("type", ""),
                              "seconds": float(str(step.get("staticDuration", "0s")).rstrip("s"))})
    return rides


def duration_seconds(envelope: dict, field: str = "duration") -> float | None:
    """`duration` (with traffic) or `staticDuration` of the first route, in seconds."""
    routes = (envelope.get("body") or {}).get("routes") or []
    if not routes or field not in routes[0]:
        return None
    return float(str(routes[0][field]).rstrip("s"))
