import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("FLOW_TICK_SECONDS", "0.02")
    monkeypatch.setenv("FLOW_CLOCK_SECONDS", "0.02")
    monkeypatch.setenv("FLOW_PING_SECONDS", "0.05")
    with TestClient(create_app()) as test_client:
        yield test_client


def test_health(client):
    body = client.get("/api/health").json()
    assert body == {"ok": True, "version": "0.1.0", "offline": False, "bucket": None,
                    "scenario": "2026-10-22-evening"}


def test_health_never_shows_the_account_id(monkeypatch):
    """AGENTS.md §17.3.7: the bucket name embeds the account ID."""
    monkeypatch.setenv("FLOW_BUCKET", "flow-data-123456789012-ap-southeast-1")
    monkeypatch.setenv("OFFLINE", "1")
    with TestClient(create_app()) as client:
        reply = client.get("/api/health")
    assert "123456789012" not in reply.text
    assert reply.json()["bucket"] == "flow-data-************-ap-southeast-1"
    assert reply.json()["offline"] is True


def test_websocket_sends_clock_and_ping(client):
    with client.websocket_connect("/ws?role=staff") as socket:
        seen = [socket.receive_json() for _ in range(8)]
    clocks = [message for message in seen if message["type"] == "clock"]
    assert len(clocks) >= 4
    assert clocks[0]["t"].endswith("+08:00")
    assert clocks[0]["payload"]["scenario_id"] == "2026-10-22-evening"
    assert clocks[0]["payload"]["playing"] is False
    assert any(message["type"] == "ping" for message in seen)


def test_pages(client):
    assert "WebSocket test" in client.get("/ws-test").text
    assert "Cathay Flow" in client.get("/").text


def test_openapi_lists_every_endpoint(client):
    paths = client.get("/openapi.json").json()["paths"]
    for path in ["/api/health", "/api/scenarios", "/api/replay/load", "/api/replay/control",
                 "/api/replay/state", "/api/passengers/{pid}/trip", "/api/passengers/{pid}/protect",
                 "/api/passengers/{pid}/options", "/api/passengers/{pid}/choose", "/api/staff/wave",
                 "/api/staff/drafts", "/api/staff/drafts/{draft_id}", "/api/staff/drafts/approve-batch",
                 "/api/impact"]:
        assert path in paths, path
