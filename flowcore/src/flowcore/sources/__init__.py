"""Cached clients for external data (AGENTS.md §7). Every live call goes through flowcore.cache."""

from __future__ import annotations

from typing import Any

import httpx

USER_AGENT = "flow-research/0.1"
TIMEOUT = 30.0


class MissingKey(RuntimeError):
    """No API key in the environment or in SSM."""


def http_client() -> httpx.Client:
    return httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})


def parse(response: httpx.Response) -> tuple[int, Any]:
    """`(status, body)`: JSON when it parses, the raw text otherwise (so errors keep their message)."""
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, response.text
