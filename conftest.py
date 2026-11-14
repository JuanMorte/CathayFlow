"""Shared test setup: tests never read the developer's .env and never reach real AWS."""

import os

import pytest

# Set before any test module imports flowcore or boto3.
os.environ["FLOW_SKIP_DOTENV"] = "1"

_CLEARED = [
    "AWS_PROFILE", "AWS_DEFAULT_PROFILE", "FLOW_BUCKET", "OFFLINE", "FLOW_REPO_ROOT",
    "OAG_KEY_DEV", "OAG_KEY_DEMO", "OAG_CONNECTIONS_KEY_DEV", "OAG_CONNECTIONS_KEY_DEMO",
    "OAG_CONNECTIONS_URL", "OAG_KEY_PROFILE", "OAG_MAX_CALLS", "GOOGLE_ROUTES_KEY",
    "GOOGLE_MAX_CALLS",
    "FLOW_PARAM_PREFIX", "FLOW_STATE_ENV",
]


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch, tmp_path):
    for name in _CLEARED:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("FLOW_SKIP_DOTENV", "1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_REGION", "ap-southeast-1")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-southeast-1")
    monkeypatch.setenv("FLOW_DATA_DIR", str(tmp_path / "data"))
    # Tests run on the real-flight replay unless they ask for another scenario.
    monkeypatch.setenv("FLOW_SCENARIO", "2026-10-22-evening")
    try:
        from flowcore import aws
    except ImportError:
        yield
        return
    aws.reset_clients()
    yield
    aws.reset_clients()
