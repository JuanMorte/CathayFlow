"""Read-through cache and call ledger: the only way to call an external API (AGENTS.md §7.1).

Lookup order: local file → S3 (copied to local on a hit) → live call. With OFFLINE=1 a miss
raises `OfflineCacheMiss` and S3 is not touched. Only 2xx responses are stored, to local and S3.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from flowcore import aws
from flowcore.config import Settings, get_settings

Call = Callable[[], tuple[int, Any]]


class OfflineCacheMiss(RuntimeError):
    """OFFLINE=1 and the response is not in the local cache."""


class BudgetExceeded(RuntimeError):
    """One more live call would pass the 30-day budget for this key."""


class SourceError(RuntimeError):
    """The API answered with a non-2xx status. Carries the API's own message (§17.4.1)."""

    def __init__(self, source: str, status: int, body: Any):
        self.source, self.status, self.body = source, status, body
        text = body if isinstance(body, str) else json.dumps(body, default=str)
        super().__init__(f"{source} answered HTTP {status}: {text[:500]}")


def make_request(source: str, url: str, params: dict | None = None, body: Any = None) -> dict:
    """The request description that is hashed, stored and logged. Never put a secret in it."""
    return {"source": source, "url": url, "params": params or {}, "body": body}


def cache_key(request: dict) -> str:
    payload = {name: request.get(name) for name in ("source", "url", "params", "body")}
    text = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(text.encode()).hexdigest()[:24]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


class Ledger:
    """One JSONL line per live call, merged with S3 so all teammates count together."""

    def __init__(self, source: str, api_key: str, budget: int,
                 settings: Settings | None = None, window_days: int = 30):
        self.s = settings or get_settings()
        self.source, self.budget, self.window = source, budget, timedelta(days=window_days)
        # Only a short hash of the key is ever stored.
        self.keyid = hashlib.sha256(api_key.encode()).hexdigest()[:8]
        self.local = self.s.data_dir / "raw" / source / f"_ledger_{self.keyid}.jsonl"
        self.s3_key = f"ledger/{source}/{self.keyid}.jsonl"

    def _remote(self) -> bool:
        return bool(self.s.bucket) and not self.s.offline

    def entries(self) -> list[dict]:
        lines: set[str] = set()
        if self.local.is_file():
            lines.update(self.local.read_text(encoding="utf-8").splitlines())
        if self._remote():
            data = aws.s3_get(self.s3_key, self.s)
            if data:
                lines.update(data.decode().splitlines())
        rows = [json.loads(line) for line in lines if line.strip()]
        return sorted(rows, key=lambda row: row["t"])

    def count(self, now: datetime | None = None) -> int:
        cutoff = ((now or _now()) - self.window).isoformat()
        return sum(1 for row in self.entries() if row["t"] >= cutoff)

    def check(self, now: datetime | None = None) -> None:
        used = self.count(now)
        if used + 1 > self.budget:
            raise BudgetExceeded(
                f"{self.source} key {self.keyid}: {used} calls in the last "
                f"{self.window.days} days, budget {self.budget}."
            )

    def record(self, status: int, request: dict, now: datetime | None = None) -> None:
        rows = self.entries()
        rows.append({"t": (now or _now()).isoformat(), "status": status, "request": request})
        text = "".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows)
        _write(self.local, text)
        if self._remote():
            aws.s3_put(self.s3_key, text.encode(), "application/x-ndjson", self.s)


class Cache:
    def __init__(self, settings: Settings | None = None):
        self.s = settings or get_settings()

    def _remote(self) -> bool:
        return bool(self.s.bucket) and not self.s.offline

    def local_path(self, source: str, key: str) -> Path:
        return self.s.data_dir / "raw" / source / f"{key}.json"

    @staticmethod
    def s3_key(source: str, key: str) -> str:
        return f"raw/{source}/{key}.json"

    def get(self, source: str, key: str) -> dict | None:
        path = self.local_path(source, key)
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        if self._remote():
            data = aws.s3_get(self.s3_key(source, key), self.s)
            if data:
                _write(path, data.decode())
                return json.loads(data)
        return None

    def put(self, source: str, key: str, envelope: dict) -> None:
        text = json.dumps(envelope, default=str)
        _write(self.local_path(source, key), text)
        if self._remote():
            aws.s3_put(self.s3_key(source, key), text.encode(), settings=self.s)

    def fetch(self, request: dict, call: Call, *, key: str | None = None,
              ledger: Ledger | None = None,
              keep: Callable[[Any], bool] = lambda body: True) -> dict:
        """Return the stored envelope, or make one live call and store it.

        `call` returns `(status, body)`. `keep(body)` False means "don't store" (e.g. an empty
        day that should be retried later, §17.4.4); the envelope is still returned.
        """
        source = request["source"]
        key = key or cache_key(request)
        hit = self.get(source, key)
        if hit is not None:
            return hit
        if self.s.offline:
            raise OfflineCacheMiss(
                f"OFFLINE=1 and no cached response for {source}/{key}: "
                f"{json.dumps(request, sort_keys=True, default=str)}"
            )
        if ledger:
            ledger.check()
        try:
            status, body = call()
        except Exception:
            if ledger:
                ledger.record(0, request)
            raise
        if ledger:
            ledger.record(status, request)
        if not 200 <= status < 300:
            raise SourceError(source, status, body)
        envelope = {"source": source, "key": key, "request": request, "status": status,
                    "fetched_at": _now().isoformat(), "body": body}
        if keep(body):
            self.put(source, key, envelope)
        return envelope
