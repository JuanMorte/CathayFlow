"""flow-recorder: a daily Lambda that stores HKIA past flights in S3 (AGENTS.md §8.2)."""

from pathlib import Path

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from constructs import Construct

from flow_infra.common import service_role

HANDLER_DIR = Path(__file__).resolve().parents[1] / "lambda" / "hkia_recorder"
RAW_HKIA = "raw/hkia/*"


class FlowRecorderStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, prefix: str, bucket: s3.IBucket,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Read + put on raw/hkia/ only, never delete (AGENTS.md §17.3.4). Listing lets a missing
        # object answer "not found" instead of "forbidden", which the skip-if-exists check needs.
        role = service_role(
            self, "RecorderRole", service="lambda.amazonaws.com",
            aws_managed=["service-role/AWSLambdaBasicExecutionRole"],
            statements=[
                iam.PolicyStatement(actions=["s3:GetObject", "s3:PutObject"],
                                    resources=[bucket.arn_for_objects(RAW_HKIA)]),
                iam.PolicyStatement(actions=["s3:ListBucket"], resources=[bucket.bucket_arn]),
            ],
        )

        log_group = logs.LogGroup(self, "Logs", retention=logs.RetentionDays.ONE_MONTH,
                                  removal_policy=RemovalPolicy.DESTROY)
        self.function = lambda_.Function(
            self, "HkiaRecorder",
            function_name=f"{prefix}-hkia-recorder",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.ARM_64,
            memory_size=256,
            timeout=Duration.seconds(120),
            handler="handler.handler",
            code=lambda_.Code.from_asset(str(HANDLER_DIR), exclude=["__pycache__"]),
            environment={"BUCKET": bucket.bucket_name},
            role=role,
            log_group=log_group,
        )

        # 18:00 UTC = 02:00 HKT, daily.
        events.Rule(self, "Daily", schedule=events.Schedule.cron(minute="0", hour="18"),
                    targets=[targets.LambdaFunction(self.function)])

        CfnOutput(self, "RecorderFunctionName", value=self.function.function_name)
