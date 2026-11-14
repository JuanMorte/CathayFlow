"""Stores every day still inside HKIA's 91-day window, by invoking the recorder Lambda in batches.

182 requests in total (91 days × arrivals and departures), spaced ≥ 1 s apart inside the Lambda.
Days already in S3 are skipped, so it is safe to run again (AGENTS.md §7.2, §17.4.4).

    make backfill-hkia            # the whole window
    uv run python scripts/backfill_hkia.py --days 3
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

from botocore.config import Config

from flowcore.config import get_settings
from flowcore.sources.hkia import WINDOW_DAYS

HKT = timezone(timedelta(hours=8))
BATCH_DAYS = 10  # 20 requests per invocation: well inside the Lambda's 120 s timeout


def window(days: int, now: datetime | None = None) -> list[str]:
    """Yesterday (HKT) and the `days - 1` days before it, newest first."""
    yesterday = (now or datetime.now(HKT)).astimezone(HKT).date() - timedelta(days=1)
    return [(yesterday - timedelta(days=back)).isoformat() for back in range(days)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--days", type=int, default=WINDOW_DAYS)
    parser.add_argument("--function", default=None, help="Lambda name (default <prefix>-hkia-recorder)")
    args = parser.parse_args()

    import boto3

    settings = get_settings()
    name = args.function or f"{settings.env('FLOW_PREFIX') or 'flow'}-hkia-recorder"
    session = boto3.Session(profile_name=settings.aws_profile, region_name=settings.aws_region)
    client = session.client("lambda", config=Config(read_timeout=180, retries={"max_attempts": 0}))

    pending = window(args.days)
    totals = {"stored": 0, "skipped": 0, "empty": 0, "failed": 0}
    errors: list[dict] = []
    rounds = 0
    while pending and rounds < 4 * (args.days // BATCH_DAYS + 1):
        rounds += 1
        batch, pending = pending[:BATCH_DAYS], pending[BATCH_DAYS:]
        reply = client.invoke(FunctionName=name, Payload=json.dumps({"dates": batch}).encode())
        result = json.loads(reply["Payload"].read())
        if reply.get("FunctionError"):
            print(f"Lambda error for {batch[0]}..{batch[-1]}: {str(result)[:300]}", file=sys.stderr)
            return 1
        for field in totals:
            totals[field] += result.get(field, 0)
        errors += result.get("errors", [])
        # Anything the Lambda ran out of time for goes back on the list.
        unfinished = sorted({key.split("past_")[1][:10] for key in result.get("not_done", [])}, reverse=True)
        pending = unfinished + pending
        print(f"{batch[0]} .. {batch[-1]}: {json.dumps({k: result.get(k, 0) for k in totals})}")

    print(f"Total: {json.dumps(totals)}")
    for error in errors[:10]:
        print(f"  {error['key']}: HTTP {error['status']} {error['message'][:120]}")
    return 1 if totals["failed"] or pending else 0


if __name__ == "__main__":
    sys.exit(main())
