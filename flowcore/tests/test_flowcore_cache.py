import json
from datetime import datetime, timedelta, timezone

import boto3
import pytest
from moto import mock_aws

from flowcore import aws
from flowcore.cache import (BudgetExceeded, Cache, Ledger, OfflineCacheMiss, SourceError,
                            cache_key, make_request)

BUCKET = "flow-test-bucket"
REGION = "ap-southeast-1"
REQUEST = make_request("oag", "https://example.test/x", {"b": 2, "a": 1})


@pytest.fixture
def cloud(monkeypatch):
    with mock_aws():
        boto3.client("s3", region_name=REGION).create_bucket(
            Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION})
        monkeypatch.setenv("FLOW_BUCKET", BUCKET)
        aws.reset_clients()
        yield boto3.client("s3", region_name=REGION)


class Counter:
    def __init__(self, status=200, body=None):
        self.calls, self.status, self.body = 0, status, {"ok": True} if body is None else body

    def __call__(self):
        self.calls += 1
        return self.status, self.body


def test_key_is_24_hex_and_ignores_param_order():
    other = make_request("oag", "https://example.test/x", {"a": 1, "b": 2})
    key = cache_key(REQUEST)
    assert len(key) == 24 and int(key, 16) >= 0
    assert key == cache_key(other)
    assert key != cache_key(make_request("oag", "https://example.test/y", {"a": 1, "b": 2}))


def test_live_call_once_then_local(cloud):
    call = Counter()
    first = Cache().fetch(REQUEST, call)
    second = Cache().fetch(REQUEST, call)
    assert call.calls == 1
    assert first == second
    assert set(first) == {"source", "key", "request", "status", "fetched_at", "body"}
    assert first["request"] == REQUEST and first["status"] == 200
    stored = cloud.get_object(Bucket=BUCKET, Key=f"raw/oag/{first['key']}.json")["Body"].read()
    assert json.loads(stored) == first


def test_s3_hit_is_copied_to_local(cloud):
    call = Counter()
    cache = Cache()
    envelope = cache.fetch(REQUEST, call)
    local = cache.local_path("oag", envelope["key"])
    local.unlink()
    assert Cache().fetch(REQUEST, call) == envelope
    assert call.calls == 1 and local.is_file()


def test_offline_miss_names_the_request_and_skips_s3(cloud, monkeypatch):
    Cache().fetch(REQUEST, Counter())
    monkeypatch.setenv("OFFLINE", "1")
    cache = Cache()
    cache.local_path("oag", cache_key(REQUEST)).unlink()
    call = Counter()
    with pytest.raises(OfflineCacheMiss, match="example.test/x"):
        cache.fetch(REQUEST, call)
    assert call.calls == 0


def test_offline_hit_works_without_aws(monkeypatch):
    Cache().fetch(REQUEST, Counter())  # no bucket: local only
    monkeypatch.setenv("OFFLINE", "1")
    assert Cache().fetch(REQUEST, Counter(status=500))["body"] == {"ok": True}


def test_errors_are_not_stored_and_keep_the_message(cloud):
    call = Counter(status=400, body={"message": "out of valid range"})
    with pytest.raises(SourceError, match="out of valid range") as err:
        Cache().fetch(REQUEST, call)
    assert err.value.status == 400
    assert Cache().get("oag", cache_key(REQUEST)) is None
    assert aws.s3_list("raw/") == []


def test_keep_false_returns_but_does_not_store(cloud):
    call = Counter(body=[])
    assert Cache().fetch(REQUEST, call, keep=bool)["body"] == []
    Cache().fetch(REQUEST, call, keep=bool)
    assert call.calls == 2


def test_ledger_counts_live_calls_only(cloud):
    ledger = Ledger("oag", "the-api-key", budget=5)
    call = Counter()
    Cache().fetch(REQUEST, call, ledger=ledger)
    Cache().fetch(REQUEST, call, ledger=ledger)
    assert ledger.count() == 1
    row = ledger.entries()[0]
    assert set(row) == {"t", "status", "request"} and row["status"] == 200
    assert "the-api-key" not in ledger.local.read_text()
    assert "the-api-key" not in ledger.local.name
    assert aws.s3_list("ledger/oag/") == [f"ledger/oag/{ledger.keyid}.jsonl"]


def test_ledger_records_failed_calls(cloud):
    ledger = Ledger("oag", "the-api-key", budget=5)
    with pytest.raises(SourceError):
        Cache().fetch(REQUEST, Counter(status=429, body="quota"), ledger=ledger)
    assert [row["status"] for row in ledger.entries()] == [429]


def test_budget_refuses_before_calling(cloud):
    ledger = Ledger("oag", "the-api-key", budget=2)
    for n in range(2):
        Cache().fetch(make_request("oag", "https://example.test/x", {"n": n}), Counter(), ledger=ledger)
    call = Counter()
    with pytest.raises(BudgetExceeded):
        Cache().fetch(make_request("oag", "https://example.test/x", {"n": 99}), call, ledger=ledger)
    assert call.calls == 0


def test_ledger_window_is_30_days(cloud):
    ledger = Ledger("oag", "the-api-key", budget=1)
    now = datetime(2026, 11, 14, tzinfo=timezone.utc)
    ledger.record(200, REQUEST, now=now - timedelta(days=31))
    assert ledger.count(now) == 0
    ledger.check(now)
    ledger.record(200, REQUEST, now=now - timedelta(days=29))
    assert ledger.count(now) == 1
    with pytest.raises(BudgetExceeded):
        ledger.check(now)


def test_ledger_merges_teammates_through_s3(cloud, tmp_path, monkeypatch):
    mine = Ledger("oag", "shared-key", budget=10)
    mine.record(200, REQUEST)
    monkeypatch.setenv("FLOW_DATA_DIR", str(tmp_path / "teammate"))
    theirs = Ledger("oag", "shared-key", budget=10)
    assert theirs.count() == 1
    theirs.record(200, REQUEST)
    assert theirs.count() == 2
    monkeypatch.setenv("FLOW_DATA_DIR", str(tmp_path / "data"))
    assert Ledger("oag", "shared-key", budget=10).count() == 2
