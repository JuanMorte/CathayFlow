"""CDK app: FlowData, FlowRecorder and FlowApp stacks (AGENTS.md §8.2).

The account and region come from the active credentials; nothing is hard-coded. Stacks deploy with
the caller's own credentials, without `cdk bootstrap` (see flow_infra/common.py).
"""

import os

import aws_cdk as cdk

from flow_infra.app_stack import FlowAppStack
from flow_infra.common import synthesizer
from flow_infra.data_stack import FlowDataStack
from flow_infra.recorder_stack import FlowRecorderStack

app = cdk.App()
prefix = app.node.try_get_context("prefix") or "flow"

env = cdk.Environment(account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
                      region=os.environ.get("CDK_DEFAULT_REGION"))

data = FlowDataStack(app, f"{prefix}-data", prefix=prefix, env=env, synthesizer=synthesizer(prefix))
FlowRecorderStack(app, f"{prefix}-recorder", prefix=prefix, bucket=data.bucket, env=env,
                  synthesizer=synthesizer(prefix))
FlowAppStack(app, f"{prefix}-app", prefix=prefix, bucket=data.bucket, task_role=data.app_task_role,
             execution_role=data.app_execution_role,
             oag_key_profile=app.node.try_get_context("oag_key_profile") or "demo",
             env=env, synthesizer=synthesizer(prefix))

app.synth()
