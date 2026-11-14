"""Source clients against a fake HTTP transport: no network, no real keys."""

from datetime import date, datetime, timedelta, timezone

import httpx
import pytest

from flowcore.cache import BudgetExceeded, OfflineCacheMiss, SourceError
from flowcore.sources import MissingKey, google_routes, hkia, oag


class Fake:
    """Records requests and answers from a function."""

    def __init__(self, answer):
        self.requests: list[httpx.Request] = []
        self._answer = answer
        self.http = httpx.Client(transport=httpx.MockTransport(self._handle))

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._answer(request)


def json_ok(body):
    return lambda request: httpx.Response(200, json=body)


# --- HKIA ---------------------------------------------------------------

def test_hkia_readable_key_and_params():
    fake = Fake(json_ok([{"date": "2026-11-13", "arrival": True, "list": [{"time": "00:05"}]}]))
    day = date(2026, 11, 13)
    envelope = hkia.fetch_past(day, True, http=fake.http)
    assert envelope["key"] == "past_2026-11-13_arr"
    assert hkia.past_key(day, False) == "past_2026-11-13_dep"
    sent = dict(fake.requests[0].url.params)
    assert sent == {"date": "2026-11-13", "lang": "en", "cargo": "false", "arrival": "true"}
    hkia.fetch_past(day, True, http=fake.http)
    assert len(fake.requests) == 1


def test_hkia_empty_day_is_retried():
    fake = Fake(json_ok([]))
    day = date(2026, 11, 13)
    assert hkia.fetch_past(day, False, http=fake.http)["body"] == []
    hkia.fetch_past(day, False, http=fake.http)
    assert len(fake.requests) == 2


def test_hkia_out_of_window_keeps_the_message():
    fake = Fake(lambda r: httpx.Response(400, json={"message": "date out of valid range"}))
    with pytest.raises(SourceError, match="out of valid range"):
        hkia.fetch_past(date(2026, 7, 25), True, http=fake.http)


# --- OAG ----------------------------------------------------------------

OAG_PARAMS = {"ArrivalDateTime": "2026-11-13", "CarrierCode": "CX", "FlightNumber": "254",
              "Content": "STATUSDETAILED"}


def test_oag_sends_key_in_header_only(monkeypatch):
    monkeypatch.setenv("OAG_KEY_DEV", "oag-secret")
    fake = Fake(json_ok({"data": [{"flightNumber": 254}], "paging": {"next": ""}}))
    envelope = oag.flight_instances(OAG_PARAMS, http=fake.http)
    request = fake.requests[0]
    assert request.headers["Subscription-Key"] == "oag-secret"
    assert "oag-secret" not in str(request.url)
    assert dict(request.url.params)["version"] == "v2"
    assert dict(request.url.params)["CodeType"] == "IATA"
    assert "oag-secret" not in str(envelope)
    assert oag.calls_used() == 1
    oag.flight_instances(OAG_PARAMS, http=fake.http)
    assert len(fake.requests) == 1 and oag.calls_used() == 1


def test_oag_refuses_requests_the_api_would_reject(monkeypatch):
    monkeypatch.setenv("OAG_KEY_DEV", "oag-secret")
    fake = Fake(json_ok({}))
    with pytest.raises(ValueError):
        oag.flight_instances({"CarrierCode": "CX"}, http=fake.http)
    with pytest.raises(ValueError):
        oag.flight_instances({"ArrivalDateTime": "2026-11-13"}, http=fake.http)
    assert fake.requests == []


def test_oag_budget_guard(monkeypatch):
    monkeypatch.setenv("OAG_KEY_DEV", "oag-secret")
    monkeypatch.setenv("OAG_MAX_CALLS", "1")
    fake = Fake(json_ok({"data": []}))
    oag.flight_instances(OAG_PARAMS, http=fake.http)
    with pytest.raises(BudgetExceeded):
        oag.flight_instances({**OAG_PARAMS, "FlightNumber": "255"}, http=fake.http)
    assert len(fake.requests) == 1


def test_oag_missing_key(monkeypatch):
    monkeypatch.setenv("OFFLINE", "0")
    monkeypatch.setattr("flowcore.aws.get_secret", lambda *a, **k: None)
    with pytest.raises(MissingKey):
        oag.flight_instances(OAG_PARAMS, http=Fake(json_ok({})).http)


def test_oag_profile_selects_key(monkeypatch):
    monkeypatch.setenv("OAG_KEY_DEV", "dev-secret")
    monkeypatch.setenv("OAG_KEY_DEMO", "demo-secret")
    monkeypatch.setenv("OAG_KEY_PROFILE", "demo")
    fake = Fake(json_ok({"data": []}))
    oag.flight_instances(OAG_PARAMS, http=fake.http)
    assert fake.requests[0].headers["Subscription-Key"] == "demo-secret"


def test_oag_next_page_follows_the_full_url(monkeypatch):
    monkeypatch.setenv("OAG_KEY_DEV", "oag-secret")
    next_url = "https://api.oag.com/flight-instances/?version=v2&After=abc"
    pages = iter([{"data": [1], "paging": {"next": next_url}}, {"data": [2], "paging": {"next": ""}}])
    fake = Fake(lambda r: httpx.Response(200, json=next(pages)))
    first = oag.flight_instances(OAG_PARAMS, http=fake.http)
    second = oag.next_page(first, http=fake.http)
    assert second["body"]["data"] == [2]
    assert str(fake.requests[1].url) == next_url
    assert oag.next_page(second, http=fake.http) is None
    assert oag.calls_used() == 2


def test_oag_connections_counts_against_the_same_account(monkeypatch):
    monkeypatch.setenv("OAG_KEY_DEV", "flight-secret")
    monkeypatch.setenv("OAG_CONNECTIONS_KEY_DEV", "conn-secret")
    monkeypatch.setenv("OAG_CONNECTIONS_URL", "https://api.oag.com/connections-test/")
    fake = Fake(json_ok({"data": []}))
    oag.connections({"DepartureAirport": "LHR", "ArrivalAirport": "SYD"}, http=fake.http)
    assert fake.requests[0].headers["Subscription-Key"] == "conn-secret"
    assert oag.calls_used() == 1


def test_oag_offline_miss(monkeypatch):
    monkeypatch.setenv("OFFLINE", "1")
    fake = Fake(json_ok({}))
    with pytest.raises(OfflineCacheMiss):
        oag.flight_instances(OAG_PARAMS, http=fake.http)
    assert fake.requests == []


# --- Google Routes ------------------------------------------------------

@pytest.fixture(autouse=True)
def _fresh_google():
    google_routes.reset_key_rejected()
    yield
    google_routes.reset_key_rejected()


WHEN = datetime(2026, 11, 21, 9, 7, 30, tzinfo=timezone(timedelta(hours=8)))
ROUTE = {"routes": [{"duration": "2105s", "staticDuration": "1810s", "distanceMeters": 34500}]}


def test_google_body_headers_and_rounding(monkeypatch):
    monkeypatch.setenv("GOOGLE_ROUTES_KEY", "g-secret")
    fake = Fake(json_ok(ROUTE))
    envelope = google_routes.compute_route("Central, Hong Kong", WHEN, traffic_model="PESSIMISTIC",
                                           http=fake.http)
    request = fake.requests[0]
    assert request.headers["X-Goog-Api-Key"] == "g-secret"
    assert request.headers["X-Goog-FieldMask"] == google_routes.FIELD_MASK
    body = envelope["request"]["body"]
    assert body["departureTime"] == "2026-11-21T01:00:00Z"
    assert body["routingPreference"] == "TRAFFIC_AWARE_OPTIMAL" and body["trafficModel"] == "PESSIMISTIC"
    assert body["destination"] == {"address": google_routes.AIRPORT}
    assert "g-secret" not in str(envelope)
    assert google_routes.duration_seconds(envelope) == 2105.0
    assert google_routes.duration_seconds(envelope, "staticDuration") == 1810.0
    # 09:14 falls in the same 15-minute bucket: served from the cache.
    google_routes.compute_route("Central, Hong Kong", WHEN + timedelta(minutes=7),
                                traffic_model="PESSIMISTIC", http=fake.http)
    assert len(fake.requests) == 1


def test_google_transit_has_no_traffic_fields(monkeypatch):
    monkeypatch.setenv("GOOGLE_ROUTES_KEY", "g-secret")
    fake = Fake(json_ok(ROUTE))
    envelope = google_routes.compute_route("Central, Hong Kong", WHEN, travel_mode="TRANSIT",
                                           http=fake.http)
    body = envelope["request"]["body"]
    assert "routingPreference" not in body and "trafficModel" not in body


def test_google_stops_after_one_key_rejection(monkeypatch):
    monkeypatch.setenv("GOOGLE_ROUTES_KEY", "g-secret")
    fake = Fake(lambda r: httpx.Response(403, json={"error": {"message": "API key not valid"}}))
    with pytest.raises(google_routes.KeyRejected, match="API key not valid"):
        google_routes.compute_route("Central, Hong Kong", WHEN, http=fake.http)
    with pytest.raises(google_routes.KeyRejected):
        google_routes.compute_route("Kowloon Station", WHEN, http=fake.http)
    assert len(fake.requests) == 1


def test_google_needs_an_aware_time():
    with pytest.raises(ValueError):
        google_routes.round_departure(datetime(2026, 11, 21, 9, 0))
