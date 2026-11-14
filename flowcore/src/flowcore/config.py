"""Settings from the environment (AGENTS.md §8.4).

Real environment variables always beat `.env` (§17.5.4), and settings are read when
`get_settings()` is called, never at import time (§17.5.3).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from dotenv import dotenv_values

DEFAULT_REGION = "ap-southeast-1"


def _truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def find_repo_root() -> Path:
    explicit = os.environ.get("FLOW_REPO_ROOT")
    if explicit:
        return Path(explicit).resolve()
    for start in (Path.cwd(), Path(__file__).resolve().parent):
        for folder in (start, *start.parents):
            if (folder / "AGENTS.md").is_file() and (folder / "flowcore").is_dir():
                return folder
    return Path.cwd()


def merged_env(repo_root: Path, dotenv_path: Path | None = None) -> dict[str, str]:
    """`.env` values first, then the real environment on top."""
    values: dict[str, str] = {}
    if not _truthy(os.environ.get("FLOW_SKIP_DOTENV")):
        path = dotenv_path or repo_root / ".env"
        if path.is_file():
            values.update({k: v for k, v in dotenv_values(path).items() if v})
    values.update({k: v for k, v in os.environ.items() if v != ""})
    return values


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    data_dir: Path
    aws_profile: str | None
    aws_region: str
    bucket: str | None
    param_prefix: str
    state_env: str
    offline: bool
    oag_key_profile: str
    oag_max_calls: int
    oag_connections_url: str | None
    google_max_calls: int
    # Kept out of repr so a printed Settings never shows a key.
    _env: Mapping[str, str] = field(default_factory=dict, repr=False, compare=False)

    def env(self, name: str) -> str | None:
        """A value from the environment or `.env`; None when unset or empty."""
        return self._env.get(name) or None


def get_settings(dotenv_path: Path | None = None) -> Settings:
    repo_root = find_repo_root()
    env = merged_env(repo_root, dotenv_path)
    get = lambda name, default=None: env.get(name) or default  # noqa: E731
    data_dir = Path(get("FLOW_DATA_DIR") or repo_root / "data")
    return Settings(
        repo_root=repo_root,
        data_dir=data_dir,
        aws_profile=get("AWS_PROFILE"),
        aws_region=get("AWS_REGION", DEFAULT_REGION),
        bucket=get("FLOW_BUCKET"),
        param_prefix=get("FLOW_PARAM_PREFIX", "/flow").rstrip("/"),
        state_env=get("FLOW_STATE_ENV", "local"),
        offline=_truthy(get("OFFLINE", "0")),
        oag_key_profile=get("OAG_KEY_PROFILE", "dev"),
        oag_max_calls=int(get("OAG_MAX_CALLS", "800")),
        oag_connections_url=get("OAG_CONNECTIONS_URL"),
        google_max_calls=int(get("GOOGLE_MAX_CALLS", "300")),
        _env=env,
    )
