"""flow-app: one Fargate task behind a load balancer and CloudFront (AGENTS.md §8.2).

Exactly one task, never two: runtime state is in memory. CloudFront gives HTTPS and passes
WebSockets through. Destroy this stack when idle (`make destroy-app`); its roles live in flow-data.
"""

from pathlib import Path

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr_assets as ecr_assets
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from constructs import Construct

REPO_ROOT = Path(__file__).resolve().parents[2]
# Kept out of the image build: secrets, caches, and everything the app does not run.
IMAGE_EXCLUDE = [
    ".git", ".github", ".venv", ".env", ".make.env", ".pytest_cache", "**/__pycache__",
    "infra", "research", "docs", "scripts", "contracts",
    "web", "backend/tests", "flowcore/tests",
    "data/raw", "data/processed", "data/state", "data/models",
]


class FlowAppStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, prefix: str, bucket: s3.IBucket,
                 task_role: iam.IRole, execution_role: iam.IRole, oag_key_profile: str = "demo",
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Public subnets only: no NAT gateway to pay for.
        vpc = ec2.Vpc(
            self, "Vpc", max_azs=2, nat_gateways=0,
            subnet_configuration=[ec2.SubnetConfiguration(
                name="public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24)],
        )
        cluster = ecs.Cluster(self, "Cluster", vpc=vpc)
        log_group = logs.LogGroup(self, "Logs", log_group_name=f"/{prefix}/app",
                                  retention=logs.RetentionDays.ONE_WEEK,
                                  removal_policy=RemovalPolicy.DESTROY)

        image = ecs.ContainerImage.from_asset(
            str(REPO_ROOT), file="Dockerfile", platform=ecr_assets.Platform.LINUX_ARM64,
            exclude=IMAGE_EXCLUDE,
        )
        service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "Service",
            cluster=cluster,
            cpu=1024,
            memory_limit_mib=2048,
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.ARM64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX),
            desired_count=1,
            min_healthy_percent=0,     # stop the old task before starting the new one:
            max_healthy_percent=100,   # never two tasks at once
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            assign_public_ip=True,
            task_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            public_load_balancer=True,
            health_check_grace_period=Duration.seconds(60),
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=image,
                container_port=8000,
                task_role=task_role,
                execution_role=execution_role,
                log_driver=ecs.LogDrivers.aws_logs(stream_prefix="app", log_group=log_group),
                environment={
                    "AWS_REGION": self.region,
                    "FLOW_BUCKET": bucket.bucket_name,
                    "OAG_KEY_PROFILE": oag_key_profile,
                    "FLOW_PARAM_PREFIX": f"/{prefix}",
                    "FLOW_STATE_ENV": "cloud",
                    "OFFLINE": "0",
                    "FLOW_REPO_ROOT": "/app",
                },
            ),
        )
        service.target_group.configure_health_check(path="/api/health")
        # 10 s, not the default 300 s, or every single-task deploy gives minutes of 503 (§17.3.5).
        service.target_group.set_attribute("deregistration_delay.timeout_seconds", "10")
        # Long-lived WebSockets.
        service.load_balancer.set_attribute("idle_timeout.timeout_seconds", "3600")

        distribution = cloudfront.Distribution(
            self, "Cdn",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.LoadBalancerV2Origin(
                    service.load_balancer,
                    protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
            ),
        )

        CfnOutput(self, "AppUrl", value=f"https://{distribution.distribution_domain_name}")
        CfnOutput(self, "AlbUrl", value=f"http://{service.load_balancer.load_balancer_dns_name}")
