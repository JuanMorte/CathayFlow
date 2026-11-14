"""HKIA recorder Lambda: stores each day of past flights in S3 before it ages out (AGENTS.md §8.2).

Standard library plus the runtime's boto3 only. Writes the same envelope as flowcore.cache
(§7.1) under raw/hkia/past_<date>_<arr|dep>.json. Only 2xx non-empty bodies are stored, so a
bad day is retried on the next run instead of being skipped forever (§17.4.4).

Event: {"dates": ["YYYY-MM-DD", ...]}; default is yesterday and the day before (HKT).
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError

URL = "https://www.hongkongairport.com/flightinfo-rest/rest/flights/past"
HKT = timezone(timedelta(hours=8))
USER_AGENT = "flow-recorder/0.1"
SLEEP_SECONDS = 1.0
STOP_BEFORE_TIMEOUT_MS = 20_000
_MISSING = {"404", "NoSuchKey", "NotFound"}


def default_dates(now=None):
    today = (now or datetime.now(HKT)).astimezone(HKT).date()
    return [(today - timedelta(days=back)).isoformat() for back in (1, 2)]


def object_key(day, arrival):
    return f"raw/hkia/past_{day}_{'arr' if arrival else 'dep'}.json"


def params_for(day, arrival):
    return {"date": day, "lang": "en", "cargo": "false", "arrival": "true" if arrival else "false"}


def exists(s3, bucket, key):
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as err:
        if err.response["Error"]["Code"] in _MISSING:
            return False
        raise


def fetch(day, arrival):
    """`(status, body)`; body is parsed JSON on success, the error text otherwise."""
    url = URL + "?" + urllib.parse.urlencode(params_for(day, arrival))
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as reply:
            return reply.status, json.loads(reply.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode("utf-8", "replace")[:500]
    except (urllib.error.URLError, TimeoutError, ValueError) as err:
        return 0, f"{type(err).__name__}: {err}"


def handler(event, context):
    bucket = os.environ["BUCKET"]
    s3 = boto3.client("s3")
    dates = (event or {}).get("dates") or default_dates()
    counts = {"stored": 0, "skipped": 0, "empty": 0, "failed": 0}
    errors, not_done, called = [], [], False

    for day in dates:
        for arrival in (True, False):
            key = object_key(day, arrival)
            remaining = context.get_remaining_time_in_millis() if context else None
            if remaining is not None and remaining < STOP_BEFORE_TIMEOUT_MS:
                not_done.append(key)
                continue
            if exists(s3, bucket, key):
                counts["skipped"] += 1
                continue
            if called:
                time.sleep(SLEEP_SECONDS)
            called = True
            status, body = fetch(day, arrival)
            if not 200 <= status < 300:
                counts["failed"] += 1
                errors.append({"key": key, "status": status, "message": str(body)[:300]})
                continue
            if not body:
                counts["empty"] += 1
                continue
            envelope = {
                "source": "hkia",
                "key": key.rsplit("/", 1)[1].removesuffix(".json"),
                "request": {"source": "hkia", "url": URL, "params": params_for(day, arrival), "body": None},
                "status": status,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "body": body,
            }
            s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(envelope).encode("utf-8"),
                          ContentType="application/json")
            counts["stored"] += 1

    result = {**counts, "errors": errors, "not_done": not_done}
    print(json.dumps(result))
    return result
