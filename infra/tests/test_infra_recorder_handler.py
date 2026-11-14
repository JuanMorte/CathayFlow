"""The recorder Lambda against a mocked S3 and a fake HKIA."""

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

BUCKET = "flow-test-bucket"
REGION = "ap-southeast-1"
HANDLER = Path(__file__).resolve().parents[1] / "lambda" / "hkia_recorder" / "handler.py"


@pytest.fixture
def recorder(monkeypatch):
    spec = importlib.util.spec_from_file_location("hkia_recorder_handler", HANDLER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    monkeypatch.setenv("BUCKET", BUCKET)
    with mock_aws():
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION})
        yield module, s3


def keys(s3):
    return sorted(item["Key"] for item in s3.list_objects_v2(Bucket=BUCKET).get("Contents", []))


def test_default_dates_are_yesterday_and_the_day_before_in_hkt(recorder):
    module, _ = recorder
    # 17:30 UTC on the 13th is already 01:30 on the 14th in Hong Kong.
    now = datetime(2026, 11, 13, 17, 30, tzinfo=timezone.utc)
    assert module.default_dates(now) == ["2026-11-13", "2026-11-12"]


def test_stores_the_cache_envelope_and_skips_existing(recorder, monkeypatch):
    module, s3 = recorder
    calls = []

    def fake_fetch(day, arrival):
        calls.append((day, arrival))
        return 200, [{"date": day, "arrival": arrival, "list": [{"time": "00:05"}]}]

    monkeypatch.setattr(module, "fetch", fake_fetch)
    first = module.handler({"dates": ["2026-11-13"]}, None)
    assert first["stored"] == 2 and first["skipped"] == 0
    assert keys(s3) == ["raw/hkia/past_2026-11-13_arr.json", "raw/hkia/past_2026-11-13_dep.json"]

    envelope = json.loads(s3.get_object(Bucket=BUCKET, Key="raw/hkia/past_2026-11-13_arr.json")["Body"].read())
    assert set(envelope) == {"source", "key", "request", "status", "fetched_at", "body"}
    assert envelope["key"] == "past_2026-11-13_arr" and envelope["source"] == "hkia"
    assert envelope["request"]["params"] == {"date": "2026-11-13", "lang": "en", "cargo": "false",
                                             "arrival": "true"}

    second = module.handler({"dates": ["2026-11-13"]}, None)
    assert second["stored"] == 0 and second["skipped"] == 2
    assert len(calls) == 2


def test_same_envelope_as_flowcore(recorder, monkeypatch):
    """The Lambda and flowcore.sources.hkia must agree on key, URL and request."""
    from datetime import date

    from flowcore.cache import make_request
    from flowcore.sources import hkia

    module, s3 = recorder
    monkeypatch.setattr(module, "fetch", lambda day, arrival: (200, [{"date": day}]))
    module.handler({"dates": ["2026-11-13"]}, None)
    day = date(2026, 11, 13)
    for arrival in (True, False):
        key = f"raw/hkia/{hkia.past_key(day, arrival)}.json"
        envelope = json.loads(s3.get_object(Bucket=BUCKET, Key=key)["Body"].read())
        assert envelope["request"] == make_request("hkia", hkia.URL, hkia.past_params(day, arrival))


def test_failed_and_empty_days_are_not_stored(recorder, monkeypatch):
    module, s3 = recorder

    def fake_fetch(day, arrival):
        return (400, "date out of valid range") if arrival else (200, [])

    monkeypatch.setattr(module, "fetch", fake_fetch)
    result = module.handler({"dates": ["2026-07-25"]}, None)
    assert result["failed"] == 1 and result["empty"] == 1 and result["stored"] == 0
    assert result["errors"][0]["status"] == 400
    assert "out of valid range" in result["errors"][0]["message"]
    assert keys(s3) == []


def test_stops_before_the_timeout(recorder, monkeypatch):
    module, s3 = recorder
    monkeypatch.setattr(module, "fetch", lambda day, arrival: (200, [{"date": day}]))

    class Context:
        def __init__(self):
            self.left = [60_000, 60_000, 5_000, 5_000]

        def get_remaining_time_in_millis(self):
            return self.left.pop(0)

    result = module.handler({"dates": ["2026-11-13", "2026-11-12"]}, Context())
    assert result["stored"] == 2
    assert result["not_done"] == ["raw/hkia/past_2026-11-12_arr.json", "raw/hkia/past_2026-11-12_dep.json"]
