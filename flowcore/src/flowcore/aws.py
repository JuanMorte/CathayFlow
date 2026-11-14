"""boto3 helpers: one session, S3 get/put, SSM secrets (AGENTS.md §6, §8.3).

Nothing here hard-codes an account ID, bucket name or key.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from flowcore.config import Settings, get_settings

log = logging.getLogger(__name__)

_clients: dict[tuple[str, str | None, str], Any] = {}
_MISSING = {"NoSuchKey", "404", "NotFound"}


class NoBucket(RuntimeError):
    """FLOW_BUCKET is not set."""


def reset_clients() -> None:
    _clients.clear()


def client(service: str, settings: Settings | None = None) -> Any:
    s = settings or get_settings()
    key = (service, s.aws_profile, s.aws_region)
    if key not in _clients:
        session = boto3.Session(profile_name=s.aws_profile, region_name=s.aws_region)
        _clients[key] = session.client(service)
    return _clients[key]


def _bucket(settings: Settings) -> str:
    if not settings.bucket:
        raise NoBucket("FLOW_BUCKET is not set (flow-data stack output 'BucketName').")
    return settings.bucket


def s3_get(key: str, settings: Settings | None = None) -> bytes | None:
    """Object bytes, or None when the key does not exist."""
    s = settings or get_settings()
    try:
        return client("s3", s).get_object(Bucket=_bucket(s), Key=key)["Body"].read()
    except ClientError as err:
        if err.response["Error"]["Code"] in _MISSING:
            return None
        raise


def s3_put(key: str, data: bytes, content_type: str = "application/json",
           settings: Settings | None = None) -> None:
    s = settings or get_settings()
    client("s3", s).put_object(Bucket=_bucket(s), Key=key, Body=data, ContentType=content_type)


def s3_exists(key: str, settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    try:
        client("s3", s).head_object(Bucket=_bucket(s), Key=key)
        return True
    except ClientError as err:
        if err.response["Error"]["Code"] in _MISSING:
            return False
        raise


def s3_list(prefix: str, settings: Settings | None = None) -> list[str]:
    s = settings or get_settings()
    pages = client("s3", s).get_paginator("list_objects_v2").paginate(Bucket=_bucket(s), Prefix=prefix)
    return [item["Key"] for page in pages for item in page.get("Contents", [])]


def get_secret(name: str, env_var: str, settings: Settings | None = None) -> str | None:
    """The env var first, then SSM `<prefix>/<name>`; None if missing (§8.3)."""
    s = settings or get_settings()
    value = s.env(env_var)
    if value:
        return value
    if s.offline:
        return None
    try:
        reply = client("ssm", s).get_parameter(Name=f"{s.param_prefix}/{name}", WithDecryption=True)
    except ClientError as err:
        if err.response["Error"]["Code"] != "ParameterNotFound":
            log.warning("SSM read failed for %s/%s: %s", s.param_prefix, name,
                        err.response["Error"]["Code"])
        return None
    except BotoCoreError as err:
        log.warning("SSM unavailable for %s/%s: %s", s.param_prefix, name, type(err).__name__)
        return None
    return reply["Parameter"]["Value"] or None


def mask(text: str) -> str:
    """Hide 12-digit AWS account IDs in anything shown or returned publicly (§17.3.7)."""
    return re.sub(r"\d{12}", "************", text)
