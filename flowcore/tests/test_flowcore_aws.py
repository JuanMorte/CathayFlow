import boto3
import pytest
from moto import mock_aws

from flowcore import aws
from flowcore.config import get_settings

BUCKET = "flow-test-bucket"
REGION = "ap-southeast-1"


@pytest.fixture
def cloud(monkeypatch):
    with mock_aws():
        boto3.client("s3", region_name=REGION).create_bucket(
            Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION})
        monkeypatch.setenv("FLOW_BUCKET", BUCKET)
        aws.reset_clients()
        yield


def test_s3_round_trip(cloud):
    assert aws.s3_get("raw/x.json") is None
    assert aws.s3_exists("raw/x.json") is False
    aws.s3_put("raw/x.json", b'{"a": 1}')
    assert aws.s3_get("raw/x.json") == b'{"a": 1}'
    assert aws.s3_exists("raw/x.json") is True
    assert aws.s3_list("raw/") == ["raw/x.json"]


def test_no_bucket_is_a_clear_error():
    with pytest.raises(aws.NoBucket):
        aws.s3_get("raw/x.json")


def test_secret_env_var_first(cloud, monkeypatch):
    boto3.client("ssm", region_name=REGION).put_parameter(
        Name="/flow/oag-key-dev", Value="from-ssm", Type="SecureString")
    assert aws.get_secret("oag-key-dev", "OAG_KEY_DEV") == "from-ssm"
    monkeypatch.setenv("OAG_KEY_DEV", "from-env")
    assert aws.get_secret("oag-key-dev", "OAG_KEY_DEV") == "from-env"


def test_secret_missing_is_none(cloud):
    assert aws.get_secret("google-routes-key", "GOOGLE_ROUTES_KEY") is None


def test_secret_offline_never_calls_ssm(monkeypatch):
    monkeypatch.setenv("OFFLINE", "1")

    def boom(*args, **kwargs):
        raise AssertionError("SSM must not be called offline")

    monkeypatch.setattr(aws, "client", boom)
    assert aws.get_secret("oag-key-dev", "OAG_KEY_DEV", get_settings()) is None


def test_mask_hides_account_ids():
    assert aws.mask("flow-data-123456789012-ap-southeast-1") == "flow-data-************-ap-southeast-1"
