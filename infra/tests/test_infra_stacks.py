"""Synthesised templates checked against AGENTS.md §8.2, §17.3 and the hackathon account's rules."""

import json

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Match, Template

from flow_infra.common import synthesizer
from flow_infra.data_stack import FlowDataStack
from flow_infra.recorder_stack import FlowRecorderStack

# Denied by the hackathon permission set: any of these in a template makes the deploy fail.
DENIED_TYPES = ["AWS::IAM::Policy", "AWS::Budgets::Budget", "AWS::IAM::User", "AWS::IAM::AccessKey",
                "AWS::CloudTrail::Trail"]


@pytest.fixture(scope="module")
def templates():
    app = cdk.App()
    data = FlowDataStack(app, "flow-data", prefix="flow", synthesizer=synthesizer("flow"))
    recorder = FlowRecorderStack(app, "flow-recorder", prefix="flow", bucket=data.bucket,
                                 synthesizer=synthesizer("flow"))
    return Template.from_stack(data), Template.from_stack(recorder)


def test_buckets_are_private_encrypted_and_retained(templates):
    data, _ = templates
    buckets = data.find_resources("AWS::S3::Bucket")
    assert len(buckets) == 2  # data + staging
    for bucket in buckets.values():
        assert bucket["DeletionPolicy"] == "Retain" and bucket["UpdateReplacePolicy"] == "Retain"
        assert bucket["Properties"]["PublicAccessBlockConfiguration"] == {
            "BlockPublicAcls": True, "BlockPublicPolicy": True,
            "IgnorePublicAcls": True, "RestrictPublicBuckets": True}
        assert "BucketEncryption" in bucket["Properties"]
    data.resource_count_is("AWS::S3::BucketPolicy", 2)  # enforce_ssl on both
    for output in ("BucketName", "AssetsBucketName", "AppRepositoryName"):
        data.has_output(output, {})


def test_image_repository_is_retained(templates):
    data, _ = templates
    data.has_resource("AWS::ECR::Repository", {
        "DeletionPolicy": "Retain", "Properties": Match.object_like({"RepositoryName": "flow-app"})})


def test_no_account_id_is_hard_coded(templates):
    for template in templates:
        text = json.dumps(template.to_json())
        assert not any(part.isdigit() and len(part) == 12 for part in text.replace('"', " ").split())


def test_nothing_the_account_denies(templates):
    for template in templates:
        for denied in DENIED_TYPES:
            template.resource_count_is(denied, 0)
        for role in template.find_resources("AWS::IAM::Role").values():
            assert "Policies" not in role["Properties"], "inline role policy (iam:PutRolePolicy is denied)"


def test_no_bootstrap_is_needed(templates):
    for template in templates:
        body = template.to_json()
        assert "BootstrapVersion" not in body.get("Parameters", {})
        assert "CheckBootstrapVersion" not in body.get("Rules", {})


def test_recorder_function(templates):
    _, recorder = templates
    recorder.has_resource_properties("AWS::Lambda::Function", {
        "Runtime": "python3.12", "Architectures": ["arm64"], "MemorySize": 256, "Timeout": 120,
        "Handler": "handler.handler", "FunctionName": "flow-hkia-recorder",
    })
    recorder.has_resource_properties("AWS::Events::Rule", {"ScheduleExpression": "cron(0 18 * * ? *)"})
    recorder.has_output("RecorderFunctionName", {})


def test_recorder_role_is_managed_only_and_kept(templates):
    _, recorder = templates
    roles = recorder.find_resources("AWS::IAM::Role")
    policies = recorder.find_resources("AWS::IAM::ManagedPolicy")
    assert len(roles) == 1 and len(policies) == 1
    for resource in [*roles.values(), *policies.values()]:
        assert resource["DeletionPolicy"] == "Retain"  # the account cannot delete them


def test_recorder_cannot_delete_and_only_writes_raw_hkia(templates):
    _, recorder = templates
    (policy,) = recorder.find_resources("AWS::IAM::ManagedPolicy").values()
    statements = policy["Properties"]["PolicyDocument"]["Statement"]
    actions = {action for statement in statements
               for action in ([statement["Action"]] if isinstance(statement["Action"], str)
                              else statement["Action"])}
    assert actions == {"s3:GetObject", "s3:PutObject", "s3:ListBucket"}
    for statement in statements:
        assert statement["Effect"] == "Allow"
        if "s3:PutObject" in statement["Action"]:
            assert "/raw/hkia/*" in json.dumps(statement["Resource"])
