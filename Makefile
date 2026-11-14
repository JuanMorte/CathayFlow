# Cathay Flow: every command the team and the agents use (AGENTS.md §8.7).
# pipefail goes on SHELL because macOS ships GNU Make 3.81, which ignores .SHELLFLAGS.
SHELL := /bin/bash -o pipefail
.DEFAULT_GOAL := help

# Plain, non-secret settings from .env. "?=" keeps real environment variables on top, so
# `OFFLINE=1 make demo` stays offline (AGENTS.md §17.5.4). Python reads the rest of .env itself;
# keys never pass through make.
ENV_KEYS := AWS_PROFILE|AWS_REGION|FLOW_BUCKET|FLOW_PREFIX
-include .make.env
.make.env: .env
	@grep -E '^($(ENV_KEYS))=' .env | sed -E -e 's/^([A-Z_]+)=/\1 ?= /' -e 's/"//g' > $@

AWS_REGION ?= ap-southeast-1
FLOW_PREFIX ?= flow
export AWS_REGION
export AWS_DEFAULT_REGION := $(AWS_REGION)
ifneq ($(strip $(AWS_PROFILE)),)
export AWS_PROFILE
endif
ifneq ($(strip $(FLOW_BUCKET)),)
export FLOW_BUCKET
endif

# CLI and library are pinned together (AGENTS.md §17.2.1); the library pin is in infra/pyproject.toml.
CDK := npx --yes aws-cdk@2.1146.1
# "broadening" asks before IAM changes. Use CDK_APPROVAL=never only after the human approved the cdk diff.
CDK_APPROVAL ?= broadening
CDK_DESTROY_FLAGS ?=
CDK_CONTEXT = -c prefix=$(FLOW_PREFIX)
MASK := sed -E 's/[0-9]{12}/************/g'

.PHONY: notebooks help setup check-profile aws-whoami cdk-bootstrap synth diff-data diff-recorder diff-app \
        deploy-data deploy-recorder secrets backfill-hkia data-down data-up check-apis dev test \
        contract lock-backend build-web deploy app-url logs demo destroy-app e2e

help:
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

setup: ## Install Python and web dependencies
	uv sync --all-packages
	@if [ -f web/package.json ]; then cd web && npm ci; fi

# Without AWS_PROFILE the AWS CLI falls back to the machine's default credentials, which may
# belong to another project. Every target that touches AWS refuses to run in that case.
check-profile:
	@test -n "$(strip $(AWS_PROFILE))" || { echo "AWS_PROFILE is not set. Create .env from .env.example and set AWS_PROFILE."; exit 1; }

aws-whoami: check-profile ## Show who the AWS credentials belong to (account ID masked)
	@echo "profile: $(AWS_PROFILE)  region: $(AWS_REGION)"
	@aws sts get-caller-identity --query Arn --output text | $(MASK)

cdk-bootstrap: ## Not used: this account denies what `cdk bootstrap` needs (see flow_infra/common.py)
	@echo "No bootstrap on this account. flow-data creates the staging bucket and image repository: run make deploy-data first."

synth: ## Synthesise the CDK app (no AWS changes)
	cd infra && $(CDK) synth $(CDK_CONTEXT) --quiet

diff-data: check-profile ## Show what deploy-data would change
	cd infra && $(CDK) diff $(FLOW_PREFIX)-data $(CDK_CONTEXT) | $(MASK)

diff-recorder: check-profile ## Show what deploy-recorder would change
	cd infra && $(CDK) diff $(FLOW_PREFIX)-recorder $(CDK_CONTEXT) | $(MASK)

diff-app: check-profile lock-backend ## Show what deploy would change
	cd infra && $(CDK) diff $(FLOW_PREFIX)-app --exclusively $(CDK_CONTEXT) | $(MASK)

deploy-data: check-profile ## Deploy the data bucket, staging bucket and image repository (first)
	@# Plain CloudFormation, not `cdk deploy`: this stack creates the staging bucket that cdk deploy needs.
	cd infra && $(CDK) synth $(FLOW_PREFIX)-data $(CDK_CONTEXT) --quiet
	aws cloudformation deploy --stack-name $(FLOW_PREFIX)-data --no-fail-on-empty-changeset \
	  --capabilities CAPABILITY_IAM \
	  --template-file infra/cdk.out/$(FLOW_PREFIX)-data.template.json
	@echo "Put this bucket name into .env as FLOW_BUCKET (it embeds the account ID: never commit it):"
	@aws cloudformation describe-stacks --stack-name $(FLOW_PREFIX)-data --output text \
	  --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue'

deploy-recorder: check-profile ## Deploy the daily HKIA recorder Lambda
	cd infra && $(CDK) deploy $(FLOW_PREFIX)-recorder $(CDK_CONTEXT) --require-approval $(CDK_APPROVAL)

secrets: check-profile ## Store API keys in SSM Parameter Store (prompts, hidden input)
	bash scripts/put_secrets.sh

backfill-hkia: check-profile ## Store every day still in HKIA's 91-day window (via the Lambda)
	uv run python scripts/backfill_hkia.py

data-down: check-profile ## Copy raw, processed and scenario data from S3 to data/
	bash scripts/data_sync.sh down

data-up: check-profile ## Copy processed and scenario data from data/ to S3
	bash scripts/data_sync.sh up

check-apis: check-profile ## Call every API once and write docs/api_check.md; ONLY=aws,hkia for some
	uv run python scripts/check_apis.py --only "$(ONLY)"

dev: ## Backend on :8000 (reload) and, when the web app exists, Vite on :5173
	@trap 'kill 0' INT TERM EXIT; \
	  uv run uvicorn app.main:app --app-dir backend --reload --port 8000 & \
	  if [ -f web/package.json ]; then (cd web && npm run dev) & fi; \
	  wait

test: ## pytest, then vitest when the web app exists
	uv run pytest
	@if [ -f web/package.json ]; then cd web && npm test; fi

e2e: build-web ## Browser test of the demo loop (uses the installed Chrome)
	cd web && npm run e2e

contract: ## Export OpenAPI to contracts/ and regenerate the web types
	uv run python scripts/export_contract.py
	@if [ -f web/package.json ]; then cd web && npx --no-install openapi-typescript ../contracts/openapi.json -o src/api/types.ts; fi

notebooks: ## Re-run the research notebooks in place (stored data only, about 4 minutes)
	OFFLINE=1 uv run jupyter nbconvert --to notebook --execute --inplace research/notebooks/*.ipynb

lock-backend: ## Write the image's exact Python versions from uv.lock
	@uv export --package flow-backend --no-dev --no-emit-workspace --no-hashes --frozen \
	  -o backend/requirements.lock > /dev/null

build-web: ## Build the web app into backend/app/static
	@if [ -f web/package.json ]; then \
	  (cd web && npm run build) && rm -rf backend/app/static && cp -R web/dist backend/app/static; \
	else echo "No web app yet: the backend serves its placeholder page."; fi

deploy: check-profile lock-backend build-web ## Build and deploy the app stack, then print its URL
	cd infra && $(CDK) deploy $(FLOW_PREFIX)-app --exclusively $(CDK_CONTEXT) --require-approval $(CDK_APPROVAL)
	@$(MAKE) --no-print-directory app-url

app-url: check-profile ## Print the deployed app's URL
	@aws cloudformation describe-stacks --stack-name $(FLOW_PREFIX)-app --output text \
	  --query 'Stacks[0].Outputs[?OutputKey==`AppUrl`].OutputValue'

logs: check-profile ## Tail the app's logs
	aws logs tail /$(FLOW_PREFIX)/app --follow

demo: build-web ## Run the full demo on http://localhost:8000; OFFLINE=1 make demo with Wi-Fi off
	@echo "Phone: http://localhost:8000/app   Staff: http://localhost:8000/staff   Impact: http://localhost:8000/impact"
	uv run uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000

destroy-app: check-profile ## Destroy the app stack only; data, recorder and roles stay
	cd infra && $(CDK) destroy $(FLOW_PREFIX)-app --exclusively $(CDK_CONTEXT) $(CDK_DESTROY_FLAGS)
