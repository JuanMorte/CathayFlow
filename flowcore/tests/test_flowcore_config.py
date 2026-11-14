from flowcore.config import get_settings


def test_defaults(monkeypatch):
    s = get_settings()
    assert s.aws_region == "ap-southeast-1"
    assert s.bucket is None and s.aws_profile is None
    assert s.offline is False
    assert s.oag_key_profile == "dev" and s.oag_max_calls == 800
    assert s.param_prefix == "/flow"


def test_environment_beats_dotenv(monkeypatch, tmp_path):
    """AGENTS.md §17.5.4: `OFFLINE=1 make demo` must not be silently online."""
    dotenv = tmp_path / ".env"
    dotenv.write_text("OFFLINE=0\nOAG_KEY_PROFILE=demo\nFLOW_BUCKET=from-dotenv\n")
    monkeypatch.setenv("FLOW_SKIP_DOTENV", "0")
    monkeypatch.setenv("OFFLINE", "1")
    monkeypatch.setenv("OAG_KEY_PROFILE", "dev")
    s = get_settings(dotenv)
    assert s.offline is True
    assert s.oag_key_profile == "dev"
    assert s.bucket == "from-dotenv"


def test_settings_read_at_call_time(monkeypatch):
    assert get_settings().offline is False
    monkeypatch.setenv("OFFLINE", "1")
    assert get_settings().offline is True


def test_repr_hides_keys(monkeypatch):
    monkeypatch.setenv("OAG_KEY_DEV", "super-secret-value")
    s = get_settings()
    assert s.env("OAG_KEY_DEV") == "super-secret-value"
    assert "super-secret-value" not in repr(s)
