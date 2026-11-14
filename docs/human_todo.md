# Human to-do

Steps only a person can do (console, keys, approvals). Tick them off as you go.

## Before M0
- [x] Hackathon rules: the prepared instructions and the team's own Figma design are fine (Alex, 2026-11-14). No pre-collected data is in this repo.
- [x] Ownership: one person (Alex) handles all the code; no roles (`AGENTS.md` §6, 2026-11-14).
- [ ] Claude Code permission rules: allow `make deploy*` and `make destroy-app`.
- [x] Local tools: AWS CLI v2 (arm64), Node 20+, Docker Desktop running, uv, Python 3.12 (checked 2026-11-14).

## Next, in this order (2026-11-14)
- [x] Hackathon account: profile `flow-hackathon` (SSO region `ap-east-1`, deploy region `ap-southeast-1`); `make aws-whoami` works (2026-11-14).
- [x] `.env` created with `AWS_PROFILE=flow-hackathon` (`BUDGET_EMAIL` is no longer used and can be deleted).
- [x] `flow-data` and `flow-recorder` deployed; `FLOW_BUCKET` set in `.env`; `make backfill-hkia` stored 182 files (2026-11-14).
- [x] `make secrets`: OAG (Flight Info, Connections; dev and demo) and Google Routes keys stored (2026-11-14).

## AWS (AGENTS.md §8.1)
- [x] Which account: the hackathon account, straight away (profile `flow-hackathon`). Region `ap-southeast-1`.
- [x] SSO profile: not needed; the hackathon profile `flow-hackathon` is used instead (2026-11-14).
- [x] Budget alert: dropped; billing is closed to participants on the hackathon account.

## Keys (stored with `make secrets`)
- [x] OAG account(s) (2026-11-14): the portal issues **three keys**; store Flight Info and Connections. Copy the Connections URL from the portal into `OAG_CONNECTIONS_URL`.
- [x] Google Routes (2026-11-14): GCP project, Routes API enabled, billing on, key unrestricted to IPs while testing.
- [x] `make check-apis` passes (2026-11-14).

## Data
- [x] Trial bucket: not used, until told otherwise (Alex, 2026-11-14; see `docs/decisions.md`).

## Demo
- [ ] `/app` on a phone + `/staff` on a laptop together; WebSocket test page 10+ min on the phone.
- [ ] Demo script 3× on the deployed URL; backup screen recording; `OFFLINE=1 make demo` with Wi-Fi off.
- [ ] `make destroy-app` when idle.
- [ ] Before pushing anywhere public: confirm the repo may contain OAG-derived timelines and the Figma photo/logo.
