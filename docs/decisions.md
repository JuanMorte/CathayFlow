# Decisions

Format: date · decision · why · who.

- 2026-11-14 · No roles: one person owns all the code, with one coding agent (`AGENTS.md` §6, `CLAUDE.md`) · the five-role split was written for a team; a single owner makes it dead weight · Alex.
- 2026-11-14 · The prepared instructions (`AGENTS.md`, `CLAUDE.md`, `docs/`) and the team's own Figma design are the only pre-made material in the repo; no pre-collected data is in it · confirmed as fine under the hackathon rules · Alex.
- 2026-11-14 · Commits stay with Alex; the agent does not commit · Alex's call · Alex.
- 2026-11-14 · The recorder Lambda is named `<prefix>-hkia-recorder` (default `flow-hkia-recorder`) rather than the bare `hkia-recorder` in AGENTS.md §8.2 · two deployments in one account must not collide, and every other resource already carries the prefix · agent, to be confirmed by Alex.
- 2026-11-14 · "CX-operated" means the first entry of HKIA's `flight` list has carrier CX; codeshares on other airlines are not Cathay connections · the first entry is the operating flight in the real data · agent.
- 2026-11-14 · For a multi-stop flight the parser's `airport` is the first origin for arrivals and the final destination for departures; all stops stay in `airports` · matches the order in the real data · agent.
- 2026-11-14 · Deploy straight to the hackathon-provided AWS account, profile `flow-hackathon`, region `ap-southeast-1` (the organisers' sign-in runs in `ap-east-1`; any deploy region is allowed) · skips the account move in AGENTS.md §8.9 with under a day left · Alex.
- 2026-11-14 · Every make target that touches AWS refuses to run without `AWS_PROFILE` · without it the AWS CLI silently used another project's default credentials on this laptop · agent.
- 2026-11-14 · Hackathon account rules change the infrastructure (AGENTS.md §8.1.4, §8.2, §17.3.10): no `cdk bootstrap` (stacks deploy with the caller's credentials; `flow-data` creates the staging bucket and image repository and is deployed with plain CloudFormation), managed policies instead of inline, roles and policies retained, budget alert dropped · the permission set denies `iam:PutRolePolicy`, role and policy deletion and edits, and `budgets:*`; a failed bootstrap would have left a stack we could not clean up · Alex approved.
- 2026-11-14 · The product has no chat assistant and no language model; the idea is dropped and removed from the spec and the code · Alex's call · Alex.
- 2026-11-14 · The app's two roles live in `flow-data`, not `flow-app` · the account cannot delete roles, and `flow-app` is destroyed and redeployed often; each redeploy would leave another pair behind · agent, approved by Alex.
- 2026-11-14 · The app's task role carries spare permissions from the first deploy: delete under `state/` only, invoke the recorder Lambda, ECS Exec channels, and CloudWatch metrics in the `Flow` namespace · its policy cannot be edited later, so likely needs go in now; each is limited to this project's resources, and nothing under `raw/` can be deleted · Alex asked for headroom; agent chose the set.
- 2026-11-14 · The CDK entry file is `infra/cdk_app.py`, not `app.py` · `app` is the backend package, and the old name shadowed it in tests · agent.
- 2026-11-14 · The image installs exact versions from `backend/requirements.lock`, exported from `uv.lock` by `make lock-backend`, and copies `backend/app` instead of installing it · AGENTS.md §8.5's `pip install ./flowcore ./backend` would ignore the lock (§17.2.1) · agent.
- 2026-11-14 · Nothing is copied from the trial bucket (no older HKIA days, so no Typhoon Noul days; no trial research results), until told otherwise. M1 backfills the live 91-day HKIA window; M4 computes the evidence fresh, with disruption days taken from inside that window · keeps all data collected during the competition · Alex.

