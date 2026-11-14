"""Calls every external API once and writes docs/api_check.md (AGENTS.md §8.6).

Live calls go through the cache and ledger. Each check prints PASS, FAIL or SKIP (no key yet) with
the API's own error message (§17.4.1). The report holds structure and field names only: no keys,
no account IDs, no raw OAG records.

    make check-apis                      # everything
    make check-apis ONLY=aws,hkia        # some checks
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

from flowcore import aws
from flowcore.cache import Cache
from flowcore.config import get_settings
from flowcore.parse.hkia import parse_body
from flowcore.sources import MissingKey, google_routes, hkia, oag

HKT = timezone(timedelta(hours=8))
REPORT = "docs/api_check.md"
CHECKS = ["aws", "hkia", "oag", "google"]


class Skip(Exception):
    pass


def mask(text: str) -> str:
    """Hide account IDs and long identifiers (letters as well as digits, §17.4.2)."""
    text = aws.mask(str(text))
    return re.sub(r"\b[A-Za-z0-9_-]{28,}\b", "<id>", text)


def paths(obj, prefix="") -> list[str]:
    """Every field path in a JSON value, lists collapsed to []."""
    found: set[str] = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            found.add(path)
            found.update(paths(value, path))
    elif isinstance(obj, list):
        for item in obj[:40]:
            found.update(paths(item, prefix + "[]"))
    return sorted(found)


def check_aws(s, out):
    arn = aws.client("sts", s).get_caller_identity()["Arn"]
    out.append(f"- Identity: `{mask(arn)}`, region `{s.aws_region}`.")
    aws.s3_put("healthcheck.txt", b"ok", "text/plain", s)
    assert aws.s3_get("healthcheck.txt", s) == b"ok"
    aws.client("s3", s).delete_object(Bucket=s.bucket, Key="healthcheck.txt")
    out.append("- S3: put, get and delete of `healthcheck.txt` in the data bucket work.")
    names = ["oag-key-dev", "oag-connections-key-dev", "oag-key-demo", "oag-connections-key-demo",
             "google-routes-key"]
    ssm = aws.client("ssm", s)
    present = []
    for name in names:
        try:
            ssm.get_parameter(Name=f"{s.param_prefix}/{name}")
            present.append(name)
        except ssm.exceptions.ParameterNotFound:
            pass
    out.append(f"- SSM: {len(present)} of {len(names)} keys stored"
               + (f" ({', '.join(present)})." if present else " (run `make secrets`)."))


def check_hkia(s, out):
    yesterday = (datetime.now(HKT) - timedelta(days=1)).date()
    for arrival in (True, False):
        envelope = hkia.fetch_past(yesterday, arrival, cache=Cache(s))
        rows = [row for row in parse_body(envelope["body"]) if row["sched_date"] == yesterday]
        where = "stand" if arrival else "gate"
        filled = sum(1 for row in rows if row[where]) / max(len(rows), 1)
        shapes = Counter(re.sub(r"\d", "9", row["status_raw"]) for row in rows).most_common(5)
        out.append(f"- {yesterday} {'arrivals' if arrival else 'departures'}: {len(rows)} flights, "
                   f"{sum(1 for row in rows if row['carrier'] == 'CX')} operated by CX, "
                   f"{where} filled {filled:.0%}. Status shapes: "
                   + "; ".join(f"`{shape}` × {count}" for shape, count in shapes) + ".")
        time.sleep(1)
    name = f"{s.env('FLOW_PREFIX') or 'flow'}-hkia-recorder"
    reply = aws.client("lambda", s).invoke(FunctionName=name,
                                           Payload=json.dumps({"dates": [yesterday.isoformat()]}).encode())
    result = json.loads(reply["Payload"].read())
    assert not reply.get("FunctionError"), mask(str(result)[:300])
    in_s3 = all(aws.s3_exists(f"raw/hkia/{hkia.past_key(yesterday, arrival)}.json", s)
                for arrival in (True, False))
    assert in_s3, "recorder ran but the files are not in S3"
    out.append(f"- Recorder Lambda `{name}` answered {json.dumps({k: result[k] for k in ('stored', 'skipped', 'empty', 'failed')})} "
               "and both files are in S3. HKIA answers AWS Lambda IPs (the backfill fetched 182 files from Lambda).")


def check_oag(s, out):
    yesterday = (datetime.now(HKT) - timedelta(days=1)).date().isoformat()
    tomorrow = (datetime.now(HKT) + timedelta(days=1)).date().isoformat()
    base = {"ArrivalAirport": "HKG", "CarrierCode": "CX", "Content": "STATUSDETAILED"}
    try:
        recent = oag.flight_instances({**base, "ArrivalDateTime": yesterday}, settings=s)
    except MissingKey as err:
        raise Skip(str(err)) from err
    old = oag.flight_instances({**base, "ArrivalDateTime": "2026-10-14"}, settings=s)
    seats = oag.flight_instances({"DepartureAirport": "HKG", "ArrivalAirport": "SIN", "CarrierCode": "CX",
                                  "DepartureDateTime": tomorrow, "Content": "SEATS"}, settings=s)
    body = recent["body"]
    records = body.get("data") or []
    out.append(f"- Top-level keys: `{sorted(body)}`; paging: `{json.dumps({k: (v if k != 'next' else bool(v)) for k, v in (body.get('paging') or {}).items()})}` "
               "(`next` is a full URL with an `After=` cursor when true).")
    detailed = next((r for r in records if r.get("statusDetails")), records[0] if records else {})
    fields = paths(detailed)
    out.append(f"- {len(records)} records on the first page; one record has {len(fields)} field paths.")
    timing = [f for f in fields if re.search(r"(estimated|actual)Time", f)]
    out.append("- Estimated and actual times: " + ", ".join(f"`{f}`" for f in timing[:24]) + ".")
    updates = detailed.get("statusDetails") or []
    stamps = [u.get("updatedAt") for u in updates if u.get("updatedAt")]
    out.append(f"- Status updates on that flight: {len(updates)}; sorted by `updatedAt`: {stamps == sorted(stamps)}; "
               f"states seen: `{sorted({u.get('state') for u in updates if u.get('state')})}`.")
    old_records = old["body"].get("data") or []
    out.append(f"- History: 2026-10-14 returns {len(old_records)} records on page one, "
               f"{sum(1 for r in old_records if r.get('statusDetails'))} with status updates.")
    seat_records = seats["body"].get("data") or []
    seat_fields = [f for f in paths(seat_records[0] if seat_records else {}) if "seat" in f.lower()]
    out.append("- SEATS (capacity, not free seats): " + (", ".join(f"`{f}`" for f in seat_fields) or "no seat fields") + ".")
    out.append(f"- OAG live calls in the last 30 days (this key): {oag.calls_used(s)} of {s.oag_max_calls}.")
    out.append("- All field paths of one record: " + ", ".join(f"`{f}`" for f in fields) + ".")


def check_google(s, out):
    when = datetime.now(timezone.utc) + timedelta(hours=2)
    try:
        upper = google_routes.compute_route("Central, Hong Kong", when, traffic_model="PESSIMISTIC", settings=s)
    except MissingKey as err:
        raise Skip(str(err)) from err
    typical = google_routes.compute_route("Central, Hong Kong", when, traffic_model="BEST_GUESS", settings=s)
    for label, envelope in (("PESSIMISTIC", upper), ("BEST_GUESS", typical)):
        out.append(f"- Central → HKIA T1, departure in 2 h, {label}: "
                   f"{google_routes.duration_seconds(envelope) / 60:.0f} min with traffic, "
                   f"{google_routes.duration_seconds(envelope, 'staticDuration') / 60:.0f} min static.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="")
    args = parser.parse_args()
    wanted = [name for name in args.only.split(",") if name] or CHECKS
    s = get_settings()
    titles = {"aws": "AWS", "hkia": "HKIA past flights", "oag": "OAG Flight Info",
              "google": "Google Routes"}
    run = {"aws": check_aws, "hkia": check_hkia, "oag": check_oag, "google": check_google}
    report = ["# API check", "",
              f"Written by `make check-apis` on {datetime.now(HKT):%Y-%m-%d %H:%M} HKT. "
              "Structure and field names only: no keys, account IDs or raw OAG records.", ""]
    failed = 0
    for name in wanted:
        lines: list[str] = []
        try:
            run[name](s, lines)
            verdict = "PASS"
        except Skip as err:
            verdict, lines = "SKIP", lines + [f"- Skipped: {err}"]
        except Exception as err:  # the report must carry the API's own message
            verdict = "FAIL"
            failed += 1
            lines.append(f"- {type(err).__name__}: {mask(str(err))[:600]}")
        print(f"{verdict}  {titles[name]}")
        for line in lines:
            print("   " + mask(line)[:300])
        report += [f"## {titles[name]}: {verdict}", "", *[mask(line) for line in lines], ""]
    with open(s.repo_root / REPORT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(report))
    print(f"Wrote {REPORT}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
