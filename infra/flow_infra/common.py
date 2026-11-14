"""Rules every stack follows on the hackathon account (AGENTS.md §8.2, §17.3).

The account's permission set denies inline role policies (`iam:PutRolePolicy`), deleting or editing
roles and policies, and anything under billing. So:

- No standard `cdk bootstrap` (its helper roles use inline policies). Stacks deploy with the caller's
  own credentials; the staging bucket and image repository that bootstrap would have made are
  created by the flow-data stack.
- Roles get **managed** policies only, and roles and policies are kept when a stack is deleted,
  because the account cannot delete them.
"""

from aws_cdk import CliCredentialsStackSynthesizer, RemovalPolicy
from aws_cdk import aws_iam as iam
from constructs import Construct


def assets_bucket_name(prefix: str, account: str = "${AWS::AccountId}", region: str = "${AWS::Region}") -> str:
    return f"{prefix}-assets-{account}-{region}"


def app_repository_name(prefix: str) -> str:
    return f"{prefix}-app"


def synthesizer(prefix: str) -> CliCredentialsStackSynthesizer:
    """Deploy with the CLI's credentials; upload code to our own bucket and repository."""
    return CliCredentialsStackSynthesizer(
        file_assets_bucket_name=assets_bucket_name(prefix),
        image_assets_repository_name=app_repository_name(prefix),
    )


def service_role(scope: Construct, construct_id: str, *, service: str, aws_managed: list[str],
                 statements: list[iam.PolicyStatement]) -> iam.IRole:
    """A role for one AWS service with managed policies only.

    Returns the role with policy updates switched off, so no construct can add an inline policy
    to it later. Get the statements right first time: the account cannot edit them afterwards.
    """
    role = iam.Role(
        scope, construct_id,
        assumed_by=iam.ServicePrincipal(service),
        managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name(name) for name in aws_managed],
    )
    role.apply_removal_policy(RemovalPolicy.RETAIN)
    if statements:
        policy = iam.ManagedPolicy(scope, f"{construct_id}Access", statements=statements, roles=[role])
        policy.apply_removal_policy(RemovalPolicy.RETAIN)
    return role.without_policy_updates()
