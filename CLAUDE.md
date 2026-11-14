# CLAUDE.md

**Read `AGENTS.md` first and follow it.** It is the single source of truth for this repo (mission, non-negotiables, contract, engine, milestones, and §17: rules learned in the trial). This file only adds Claude Code specifics. If the two ever disagree, `AGENTS.md` wins; tell the human about the conflict.

## Every session

1. Re-read `AGENTS.md` §1 Mission, §2 Non-negotiables, §13 Current milestone, §17 Rules learned in the trial.
2. Check `docs/build_log.md` and `docs/decisions.md` for what this build has already learned and decided.

## How to work

- **Plan mode first** for any task over ~50 lines or touching more than 2 files: present the plan, wait for approval, then implement.
- **Use `make` targets**, not ad-hoc commands: `make dev`, `make test`, `make contract`, `make demo`, `OFFLINE=1 make demo`.
- **After changing a backend endpoint or schema:** run `make contract` so `contracts/openapi.json`, `web/src/api/types.ts` and `contracts/fixtures/` regenerate.
- **Before saying a task is done:** run `make test` and check its own exit code; for UI work, run the app and compare the screen with `docs/design/` at 390×844 and 1440×900; for engine work, show one worked example with numbers.
- **Parallel work:** one person owns all the code (no roles, `AGENTS.md` §6). A second, parallel Claude Code session uses its own git worktree and branch (`git worktree add ../flow-<task> -b <task>`). Never two sessions in the same folder.
- **Subagents** are fine for read-only exploration. Do edits yourself.
- **External calls:** never call OAG or Google directly from a test or a loop. Go through `flowcore/sources/` (cache + ledger). Check the OAG ledger before any live pull and report how many calls you used.
- **AWS:** use the `flow` profile (`AWS_PROFILE=flow`) and region `ap-southeast-1`. Change infrastructure only through CDK in `infra/`. Show the `cdk diff` and **ask before every `cdk deploy`**. Never destroy `flow-data` or delete objects under `raw/` in S3. Tests use `moto`, never real AWS.
- **Commits:** small, conventional messages, ending with the attribution trailer your environment specifies. Don't push or merge to `main` unless the human asks.

## Claude Code specifics learned in the trial

- **Permissions first:** ask the human to add allow rules for `make deploy*` and `make destroy-app` before M3; the auto-mode classifier blocks infrastructure applies otherwise. Never work around a classifier or safety block: stop and tell the human.
- **Shell heredocs** containing `rm -rf` (or that the safety check can't parse) are blocked: write such files with the Write/Edit tools.
- **zsh** (macOS default) doesn't word-split variables: use arrays or `xargs`; avoid echo lines made only of `=` characters.
- **Never chain** `test | tail && git commit`: run the test, check its exit code, then commit.
- **Scripted edits:** assert that each replacement matched; prefer the Edit tool for exact multi-line changes.
- **Interactive prompts** (`cdk deploy` IAM approval, `cdk destroy` y/n, `-i` git flags) can't be answered by an agent: use the Makefile variables `CDK_APPROVAL` and `CDK_DESTROY_FLAGS` (AGENTS.md §17.3).
- **Figma MCP:** on a Starter plan, use at most one or two `get_design_context` calls; work from `docs/design/*.png`.
- **Secrets:** never print a key, account ID or the human's email; mask them in reports and in anything sent to an outside service.

## Log as you go

When you hit friction (an unclear instruction, a wrong assumption, a data surprise, a test you had to fix twice), add a line to `docs/build_log.md` under the current milestone, and propose the rule for `AGENTS.md` §17 that would have prevented it.
