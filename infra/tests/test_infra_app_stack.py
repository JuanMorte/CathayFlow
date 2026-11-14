"""The app stack and the app's roles, checked against AGENTS.md §8.2 and the account's rules."""

import json

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Match, Template

from flow_infra.app_stack import IMAGE_EXCLUDE, FlowAppStack
from flow_infra.common import synthesizer
from flow_infra.data_stack import FlowDataStack


@pytest.fixture(scope="module")
def templates():
    app = cdk.App()
    data = FlowDataStack(app, "flow-data", prefix="flow", synthesizer=synthesizer("flow"))
    stack = FlowAppStack(app, "flow-app", prefix="flow", bucket=data.bucket,
                         task_role=data.app_task_role, execution_role=data.app_execution_role,
                         synthesizer=synthesizer("flow"))
    return Template.from_stack(data), Template.from_stack(stack)


def actions_of(policy: dict) -> set[str]:
    found = set()
    for statement in policy["Properties"]["PolicyDocument"]["Statement"]:
        actions = statement["Action"]
        found.update([actions] if isinstance(actions, str) else actions)
    return found


def test_app_stack_creates_no_roles_or_policies(templates):
    """Roles live in flow-data: the account cannot delete them, and flow-app is destroyed often."""
    _, app = templates
    for kind in ("AWS::IAM::Role", "AWS::IAM::Policy", "AWS::IAM::ManagedPolicy", "AWS::Lambda::Function"):
        app.resource_count_is(kind, 0)
    assert not [name for name, res in app.to_json()["Resources"].items()
                if res["Type"].startswith("Custom::")]
    assert "BootstrapVersion" not in app.to_json().get("Parameters", {})


def test_exactly_one_task_and_never_two(templates):
    _, app = templates
    app.has_resource_properties("AWS::ECS::Service", {
        "DesiredCount": 1,
        "LaunchType": "FARGATE",
        "HealthCheckGracePeriodSeconds": 60,
        "DeploymentConfiguration": Match.object_like({
            "MinimumHealthyPercent": 0, "MaximumPercent": 100,
            "DeploymentCircuitBreaker": {"Enable": True, "Rollback": True}}),
        "NetworkConfiguration": {"AwsvpcConfiguration": Match.object_like({"AssignPublicIp": "ENABLED"})},
    })


def test_task_definition(templates):
    _, app = templates
    app.has_resource_properties("AWS::ECS::TaskDefinition", {
        "Cpu": "1024", "Memory": "2048",
        "RuntimePlatform": {"CpuArchitecture": "ARM64", "OperatingSystemFamily": "LINUX"},
    })
    (task,) = app.find_resources("AWS::ECS::TaskDefinition").values()
    (container,) = task["Properties"]["ContainerDefinitions"]
    assert container["PortMappings"][0]["ContainerPort"] == 8000
    env = {item["Name"]: item["Value"] for item in container["Environment"]}
    assert env["OFFLINE"] == "0" and env["FLOW_REPO_ROOT"] == "/app" and env["FLOW_STATE_ENV"] == "cloud"
    assert env["FLOW_PARAM_PREFIX"] == "/flow" and env["OAG_KEY_PROFILE"] == "demo"
    assert not [name for name in env if "KEY" in name and name != "OAG_KEY_PROFILE"]  # no secrets in env


def test_no_nat_gateway(templates):
    _, app = templates
    app.resource_count_is("AWS::EC2::NatGateway", 0)


def test_load_balancer_settings(templates):
    _, app = templates
    app.has_resource_properties("AWS::ElasticLoadBalancingV2::TargetGroup", {
        "HealthCheckPath": "/api/health",
        "TargetGroupAttributes": Match.array_with([
            {"Key": "deregistration_delay.timeout_seconds", "Value": "10"}]),
    })
    app.has_resource_properties("AWS::ElasticLoadBalancingV2::LoadBalancer", {
        "LoadBalancerAttributes": Match.array_with([
            {"Key": "idle_timeout.timeout_seconds", "Value": "3600"}]),
    })


def test_cloudfront_passes_everything_through_over_https(templates):
    _, app = templates
    app.has_resource_properties("AWS::CloudFront::Distribution", {
        "DistributionConfig": Match.object_like({
            "DefaultCacheBehavior": Match.object_like({
                "ViewerProtocolPolicy": "redirect-to-https",
                "AllowedMethods": Match.array_with(["POST", "DELETE"]),
            }),
            "Origins": [Match.object_like({
                "CustomOriginConfig": Match.object_like({"OriginProtocolPolicy": "http-only"})})],
        }),
    })
    app.has_output("AppUrl", {})
    app.has_output("AlbUrl", {})


def test_app_roles_are_managed_only_kept_and_cannot_delete(templates):
    data, _ = templates
    roles = data.find_resources("AWS::IAM::Role")
    policies = data.find_resources("AWS::IAM::ManagedPolicy")
    assert len(roles) == 2 and len(policies) == 1
    data.resource_count_is("AWS::IAM::Policy", 0)
    for resource in [*roles.values(), *policies.values()]:
        assert resource["DeletionPolicy"] == "Retain"
        assert "Policies" not in resource["Properties"]
    (policy,) = policies.values()
    assert actions_of(policy) == {
        "s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:DeleteObject",
        "ssm:GetParameter", "ssm:GetParameters", "kms:Decrypt", "lambda:InvokeFunction",
        "ssmmessages:CreateControlChannel", "ssmmessages:CreateDataChannel",
        "ssmmessages:OpenControlChannel", "ssmmessages:OpenDataChannel", "cloudwatch:PutMetricData"}
    for statement in policy["Properties"]["PolicyDocument"]["Statement"]:
        if "s3:DeleteObject" in statement["Action"]:  # delete only replay snapshots, never raw/
            assert json.dumps(statement["Resource"]).rstrip('"]}').endswith("/state/*")
        if "lambda:InvokeFunction" in statement["Action"]:
            assert "function:flow-hkia-recorder" in json.dumps(statement["Resource"])
        assert "iam:" not in json.dumps(statement["Action"])
    text = json.dumps(policy)
    assert ":parameter/flow/*" in text.replace('", "', "").replace('","', "")
    assert "kms:ViaService" in text


def test_image_build_leaves_out_secrets_and_bulk():
    for path in (".env", ".git", "infra", "research", "data/raw", "web"):
        assert path in IMAGE_EXCLUDE
