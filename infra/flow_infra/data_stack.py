"""flow-data: the data bucket, the staging bucket and image repository CDK uploads code to, and the
app's two roles (AGENTS.md §8.2). Deploy this stack first. Never destroy it.

The app's roles live here, not in flow-app, because the account cannot delete roles: flow-app is
destroyed and redeployed many times and would leave a new pair behind each time.
"""

from aws_cdk import ArnFormat, CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from constructs import Construct

from flow_infra.common import app_repository_name, assets_bucket_name, service_role


class FlowDataStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, prefix: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # RETAIN: HKIA history can't be downloaded again once it ages out of the 91-day window.
        self.bucket = s3.Bucket(
            self, "Data",
            bucket_name=f"{prefix}-data-{self.account}-{self.region}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=False,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # What `cdk bootstrap` would have created: where Lambda code and the app image are uploaded.
        self.assets_bucket = s3.Bucket(
            self, "Assets",
            bucket_name=assets_bucket_name(prefix, self.account, self.region),
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[s3.LifecycleRule(expiration=Duration.days(30))],
        )
        self.app_repository = ecr.Repository(
            self, "AppImages",
            repository_name=app_repository_name(prefix),
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[ecr.LifecycleRule(max_image_count=5)],
        )

        # What the running app may do: read and write the data bucket (never delete) and read its
        # keys from Parameter Store. Fixed at first deploy: the account cannot edit policies.
        self.app_task_role = service_role(
            self, "AppTaskRole", service="ecs-tasks.amazonaws.com", aws_managed=[],
            statements=[
                iam.PolicyStatement(actions=["s3:GetObject", "s3:PutObject"],
                                    resources=[self.bucket.arn_for_objects("*")]),
                iam.PolicyStatement(actions=["s3:ListBucket"], resources=[self.bucket.bucket_arn]),
                iam.PolicyStatement(
                    actions=["ssm:GetParameter", "ssm:GetParameters"],
                    resources=[self.format_arn(service="ssm", resource="parameter", resource_name=f"{prefix}/*")]),
                iam.PolicyStatement(
                    actions=["kms:Decrypt"], resources=["*"],
                    conditions={"StringEquals": {"kms:ViaService": f"ssm.{self.region}.amazonaws.com"}}),
                # Spare permissions, added up front because the policy cannot be edited later.
                # Each is limited to this project's own resources.
                # Clean up old replay snapshots. Never raw/: HKIA history cannot be fetched again.
                iam.PolicyStatement(actions=["s3:DeleteObject"],
                                    resources=[self.bucket.arn_for_objects("state/*")]),
                # Ask the recorder for a missing day.
                iam.PolicyStatement(
                    actions=["lambda:InvokeFunction"],
                    resources=[self.format_arn(service="lambda", resource="function",
                                               resource_name=f"{prefix}-hkia-recorder",
                                               arn_format=ArnFormat.COLON_RESOURCE_NAME)]),
                # Open a shell in the running container for debugging (ECS Exec).
                iam.PolicyStatement(
                    actions=["ssmmessages:CreateControlChannel", "ssmmessages:CreateDataChannel",
                             "ssmmessages:OpenControlChannel", "ssmmessages:OpenDataChannel"],
                    resources=["*"]),
                # Publish the app's own metrics.
                iam.PolicyStatement(
                    actions=["cloudwatch:PutMetricData"], resources=["*"],
                    conditions={"StringEquals": {"cloudwatch:namespace": "Flow"}}),
            ],
        )
        # What ECS needs to start the container: pull the image and write logs.
        self.app_execution_role = service_role(
            self, "AppExecutionRole", service="ecs-tasks.amazonaws.com",
            aws_managed=["service-role/AmazonECSTaskExecutionRolePolicy"], statements=[],
        )

        CfnOutput(self, "BucketName", value=self.bucket.bucket_name)
        CfnOutput(self, "AssetsBucketName", value=self.assets_bucket.bucket_name)
        CfnOutput(self, "AppRepositoryName", value=self.app_repository.repository_name)
