# AGENTS.md: Cathay Flow

This file is the single source of truth for every coding agent in this repo: Claude Code, GitHub Copilot, Cursor or any other. `CLAUDE.md` and `.github/copilot-instructions.md` only point here.

Read it fully before writing code. At the start of every session, re-read **§1 Mission**, **§2 Non-negotiables**, **§13 Current milestone** and **§17 Rules learned in the trial**. If a chat request conflicts with this file, stop and ask the human.

> **This is the competition repo** for the Cathay Hackathon Development Stage (Sat 14 Nov 11:00 to Sun 15 Nov 11:00, HKT). It is built from scratch from this file, the design in `docs/design/` and the lessons of a full trial run, which are folded in as rules in **§17 (read it before M0)**. No code, contract or research result was copied from the trial: the API contract is generated again from the code (§10), and the research is redone on fresh data (§9).
>
> The infrastructure may run on a personal AWS account first and on the hackathon-provided account later (§8.9), so **nothing may hard-code an account ID, bucket name or key**.

---

## 1. Mission

**Cathay Hackathon 2026, Student Track, Premium Travel #1: "Reimagining the Premium Travel Experience"** (personalised, anticipatory).

**Cathay Flow** predicts how much time each passenger needs to reach their gate, and acts when it isn't enough. One engine (**time to gate**) serves two features:

| Feature | Who | Question | What it does |
|---|---|---|---|
| **Connection Protect** (hero) | Passengers connecting at Hong Kong (HKG) | "Will I make my connection?" | Predicts a range for when the passenger can be at the departure gate, compares it with gate close (15 min before departure), and gives a chance of missing. At risk: a backup seat is held and fast-track can be offered. Won't make it: a rebooking is drafted, **staff approve it**, then the passenger chooses, all before landing. |
| **Gate Planner** | Passengers departing from HKG | "When should I leave?" | Door-to-gate time with a safe upper estimate (road + check-in + security/immigration + walk) and a leave-by time. Re-plans when the gate or traffic changes. |

Both sit inside the **Flow app shell**: five journey stages, *Prepare, Navigate, Protect, Bags, Arrive*. Protect and Gate Planner (inside Prepare/Navigate) are real. The other stages are polished but static.

**The insight:** for premium travellers, premium means certainty. They want to know they'll make it, and to have problems fixed before they have to ask.

**How we win against teams with the same AI coding agents:** not with more screens, but with **one closed loop that works on real Hong Kong data**, shown on two synchronised screens (passenger phone and staff console), plus **evidence** (the impact panel). Every feature should make the demo story in §3 more convincing.

---

## 2. Non-negotiables (never violate; each has a test)

1. **The original seat is never released early.** It is released only when (a) the passenger explicitly picks an alternative, or (b) gate close passes and the passenger has not boarded. Guard every code path that releases a seat; test it.
2. **No rebooking without staff approval.** The engine drafts rebookings automatically; a human approves in the staff console; only then is the option offered to the passenger as confirmed.
3. **The passenger chooses.** No silent rebooking. A held backup seat is a *hold*, not a booking.
4. **Hard fairness rules beat scores.** Families/groups move together or not at all. Passengers with declared assistance needs are always protected first. Loyalty tier is a weight, never an override.
5. **No invented facts.** Every flight number, time, seat, probability or price on a screen comes from the engine, the policy or a scenario file. Staff rationales are templates filled with structured fields; a test asserts each number and flight number in a rationale equals the draft's fields.
6. **Real vs synthetic is always visible.** Every number shown carries a source label: `REAL` (HKIA/OAG/Google data), `ASSUMED` (our parameter), `SYNTHETIC` (generated passengers/bookings) or `SIMULATED` (output of a simulation). Show the label in the UI (small badge or tooltip) and keep it in the API payload.
   *Amended 2026-11-13 (Alex):* the **passenger app** (`/app`) follows the Figma Cathay design and shows **no badges**; labels stay in every API payload, in the staff console and impact panel, and in a one-line "sample data" note in the passenger footer. Details the design needs but no source has (Asia Miles, terminals, lounge, walking pace, bag tags/scans, origin departure and destination arrival times, arrival queues, taxi times) are **demo sample data**, generated deterministically in one file, `web/src/app/flow/sample.ts`, and disclosed in `README.md`. Nothing from `sample.ts` feeds the engine, policy, staff console or evidence.
7. **No leakage.** A prediction made at replay time *t* only uses information available at *t*.
8. **Respect APIs and budgets.** All external calls go through the read-through cache and call ledger (§7.1). OAG is capped at 1,000 calls per 30 days per key. Never call an external API in a loop or a test without the cache.
9. **No secrets, account IDs or OAG raw data in git.** Keys live in SSM Parameter Store or a gitignored `.env`. Raw OAG responses stay in S3 (their terms may not allow publishing them, and the submitted repo may be public).
10. **Never invent numbers in UI copy.** If a number isn't from the engine, a scenario file or `evidence.json`, it doesn't go on screen. *Exception (2026-11-13):* passenger-app sample data from `web/src/app/flow/sample.ts` (see 6). JSX copy itself still contains no digits (`web/src/copy.test.ts`).

---

## 3. The demo story (build everything toward this)

The final pitch is **5 minutes + 5 minutes Q&A**; the live demo gets about **2 minutes**. It must also run with Wi-Fi off (local, cached).

1. **Mei** (SYNTHETIC passenger, Business) is on a real Cathay inbound to HKG on a real day, connecting to a real Cathay outbound. The replay clock starts ~2 h before her landing.
2. Her inbound slips (real delay on that day). Her phone turns **At risk**: "At the gate ~18:55 · gate closes 19:30 · you'll need 25–40 min". A backup seat on a later flight is **already held**; her original seat stays hers.
3. Switch to the **staff console**: the same arrival wave shows every at-risk connecting passenger. The engine has **drafted rebookings** for those who won't make it, each with a one-line reason. Staff approve the batch (one click, per-row override).
4. Back to the phone: Mei sees **"Choose before you land"**: go for her original flight with fast-track and an escort, switch to the held seat, or stay overnight. She taps one; the console updates within a second.
5. **Impact panel**: on real days, how often tight connections break, how many missing passengers got a plan before landing, and zero wrong bumps compared with an AURA-style auto-rebook.

**Choosing Mei's connection:** don't invent it. From the scenario day, pick a real CX inbound → CX outbound pair (50–89 min scheduled connection) where the engine's chance of missing ~90 min before landing is 30–60%, and where at least one later CX flight to the same destination exists that day or next morning. Record the pick in `data/scenarios/<id>/README.md`.

UI design follows the Figma screens in `docs/design/` (`README.md` there lists each screen, its tokens and components). Match them screen by screen; where a screen shows a value no source has, see non-negotiables 6 and 10.

---

## 4. Architecture

```
 Data in                          AWS (ap-southeast-1)                                   Users
 ───────                          ────────────────────                                   ─────
 HKIA past flights ──► Lambda "hkia-recorder" (daily 02:00 HKT) ──► S3 raw/hkia/
 OAG / Google ───────► flowcore cached clients (laptop or app) ──► S3 raw/oag/, raw/google/ + ledger/
                                                                        │
 research/ (laptop) ── reads S3 ─► trains models, backtests ──► S3 models/, evidence/  ─┐
                                                                                         ▼
                      CloudFront (HTTPS, WebSockets) ─► ALB ─► ECS Fargate: 1 task (FastAPI + built React app)
                                                                    │  replay clock → engine → policy → WS push
                                                                              ▲
                                     Passenger phone (/app) · Staff console (/staff) · Impact (/impact)
```

- **The replay clock** is the heartbeat. Each tick (default 1 simulated minute): reveal what is known at *t* → engine recomputes affected connections → policy updates states → push changes over WebSocket to every open screen.
- **One backend process.** FastAPI serves the API, the WebSocket and the built frontend. **Exactly one ECS task** (in-memory state; a second task would split approvals from phones).
- **No database server.** Files: Parquet + JSON, queried with DuckDB where useful. Runtime state (holds, drafts, choices) in memory, snapshotted to `data/state/` (and S3 `state/`) every minute so a restart resumes. Production would use Postgres + an event stream; say so in the pitch, don't build it.
- **Why not App Runner:** it does not support incoming WebSockets, and the two synced screens need them. ECS Fargate behind an ALB does; CloudFront in front gives HTTPS and also supports WebSockets.

---

## 5. Stack

| Layer | Choice |
|---|---|
| Python | 3.12, **uv workspace** (members: `flowcore`, `backend`, `research`, `infra`) |
| Shared core | `flowcore`: config, AWS helpers (boto3), cached clients, model registry, **engine** |
| Backend | FastAPI, Uvicorn (`[standard]` for WebSockets), Pydantic v2, httpx, boto3 |
| Engine | NumPy (vectorised Monte Carlo), LightGBM (outbound delay, optional), OR-Tools CP-SAT (seat allocation) |
| Research | pandas or polars, DuckDB, LightGBM, scikit-learn, matplotlib, Jupyter (in `research/` only) |
| Tests | pytest (+ `moto` to mock S3/SSM), Vitest, one Playwright end-to-end test |
| Frontend | React 18 + Vite + TypeScript, Tailwind, shadcn/ui, Framer Motion, TanStack Query, React Router |
| Types | FastAPI OpenAPI → `openapi-typescript` → `web/src/api/types.ts` (generated, never hand-edited) |
| Infrastructure | **AWS CDK v2 in Python** (`infra/`), CLI run with `npx aws-cdk@2` (no global install needed) |
| AWS services | S3, Lambda, EventBridge, ECR (via CDK asset), ECS Fargate, ALB, CloudFront, SSM Parameter Store, CloudWatch Logs |

Don't add: a database server, Redis, auth, App Runner, API Gateway, Kubernetes, NAT gateways, AWS Copilot CLI (end of support announced 2026).

---

## 6. Repository layout (monorepo)

The app, the shared core, research and infrastructure live in **one repo**. Reason: the backtests that produce our evidence must run **the same engine code** as the app (`flowcore`), so the numbers on the impact panel are traceable. `research/` never imports `backend/`, and `backend/` never imports `research/`.

```
.
├── AGENTS.md · CLAUDE.md · README.md
├── .github/copilot-instructions.md      # "Follow AGENTS.md"
├── .env.example · .gitignore · .dockerignore
├── Makefile
├── pyproject.toml                        # uv workspace root (no package)
├── flowcore/                             # shared core (installable package)
│   ├── pyproject.toml
│   ├── src/flowcore/
│   │   ├── config.py                     # Settings from env (§8.4)
│   │   ├── aws.py                        # boto3 session, S3 get/put, SSM get_secret
│   │   ├── cache.py                      # read-through cache + call ledger (§7.1)
│   │   ├── sources/hkia.py · oag.py · google_routes.py
│   │   ├── parse/hkia.py                 # status-string parser → tidy flights table
│   │   ├── models.py                     # model registry: load artifact by name from S3 (§9)
│   │   └── engine/                       # time_to_gate.py, inbound.py, outbound.py, transfer.py,
│   │                                     # gate_planner.py, baselines.py (R0, R1)
│   └── tests/                            # parsers on saved fixtures, engine tiny cases, cache/ledger with moto
├── backend/
│   ├── pyproject.toml                    # depends on flowcore (workspace)
│   ├── app/
│   │   ├── main.py                       # FastAPI, static files, WS, startup: load scenario + models
│   │   ├── schemas.py                    # API contract (§10)
│   │   ├── api/                          # replay, passenger, staff, planner, impact routers
│   │   ├── replay/                       # clock.py, scenario.py, visibility.py (what is known at t)
│   │   ├── policy/                       # states.py, holds.py, drafts.py, allocate.py, expedite.py, rationale.py
│   │   ├── state.py                      # in-memory store + snapshot to data/state and S3 state/
│   │   └── static/                       # built frontend (copied by `make build-web`; gitignored)
│   └── tests/                            # test_demo_path.py (GOLDEN), test_nonnegotiables.py, ...
├── web/                                  # React app: /app, /staff, /impact
├── research/
│   ├── pyproject.toml                    # depends on flowcore + heavy libs
│   ├── README.md                         # how to reproduce every number in evidence.json
│   ├── flowresearch/
│   │   ├── build_dataset.py              # S3 raw/hkia → processed/flights.parquet (via flowcore.parse)
│   │   ├── synth.py                      # synthetic connections + passengers (seeded)
│   │   ├── train_outbound_delay.py       # → models/outbound_delay/<version>/ in S3
│   │   ├── fit_taxi_in.py                # → models/taxi_in/<version>/
│   │   ├── backtest.py                   # R0 / R1 / M1 at T−90/60/30, using flowcore.engine
│   │   ├── simulate_policies.py          # TODAY / FLOW / AURA-style on real waves
│   │   └── build_evidence.py             # → evidence.json (labels + sources)
│   └── notebooks/                        # EDA only; import from flowresearch/flowcore
├── infra/
│   ├── pyproject.toml                    # aws-cdk-lib, constructs
│   ├── cdk.json                          # "app": "uv run python cdk_app.py", context defaults (§8.2)
│   ├── cdk_app.py                        # FlowData, FlowRecorder, FlowApp stacks (not app.py: that name is the backend package)
│   ├── flow_infra/data_stack.py · recorder_stack.py · app_stack.py
│   └── lambda/hkia_recorder/handler.py   # stdlib only (urllib + boto3 from the runtime)
├── scripts/
│   ├── put_secrets.sh                    # stores keys in SSM (§8.3)
│   ├── check_apis.py                     # calls every API once → docs/api_check.md (§8.6)
│   ├── backfill_hkia.py                  # invokes the recorder Lambda for the whole 91-day window
│   ├── data_sync.sh                      # aws s3 sync raw/processed/scenarios ↔ data/
│   └── export_contract.py
├── contracts/openapi.json · contracts/fixtures/
├── config/engine.yaml · config/policy.yaml   # every ASSUMED parameter, with comment + source
├── data/                                 # local mirror of S3 (gitignored except reference/, scenarios/, evidence.json)
│   ├── reference/hkg_zones.yaml          # stand/gate zones + walking distances (ASSUMED, documented)
│   ├── scenarios/<id>/                   # flights.parquet, passengers.parquet, connections.parquet, README.md
│   └── evidence.json
├── docs/ demo-script.md · decisions.md · api_check.md · build_log.md · design/
└── Dockerfile                            # backend image (§8.5)
```

**Ownership:** one person (Alex) owns all the code and works with one coding agent. There are no roles and no per-folder owners (decided 2026-11-14).

**Files that need care:**
- `contracts/openapi.json`, `web/src/api/types.ts` and `contracts/fixtures/` are generated: change `backend/app/schemas.py` or an endpoint, then run `make contract`. Never hand-edit them.
- `AGENTS.md` and `infra/`: change only when the human agrees.

**Branches:** one agent session per folder. A second, parallel session uses its own worktree and branch (`git worktree add ../flow-<task> -b <task>`) and is merged back only when `make test` passes. Commit small and often. Front-end work runs from `contracts/fixtures/` until the backend has the fields. After the agreed freeze time, only bug fixes go to `main`.

---

## 7. Data sources

### 7.1 Cache and ledger (`flowcore/cache.py`): the only way to call an external API

- **Cache key:** first 24 hex chars of SHA-256 over the JSON (sorted keys) of `{"source": ..., "url": ..., "params": ..., "body": ...}` with **no secrets** inside. HKIA uses readable keys instead: `past_<YYYY-MM-DD>_<arr|dep>`.
- **Envelope** stored per response: `{source, key, request, status, fetched_at (ISO UTC), body}`.
- **Lookup order:** `data/raw/<source>/<key>.json` → `s3://$FLOW_BUCKET/raw/<source>/<key>.json` (download to local on hit) → live call (unless `OFFLINE=1`, which raises `OfflineCacheMiss` naming the request).
- **Write:** only 2xx responses, to local **and** S3.
- **Ledger** (OAG and Google): one JSONL line per live call `{t, status, request}` at `data/raw/<source>/_ledger_<keyid>.jsonl`, mirrored to `s3://$FLOW_BUCKET/ledger/<source>/<keyid>.jsonl` (merged on load, so all teammates count together). `keyid` = first 8 hex of SHA-256 of the API key (never store the key). Before a live call, refuse with `BudgetExceeded` if calls in the last 30 days + 1 > budget.

### 7.2 HKIA past flights (whole days, history, stands) — free, no key

- `GET https://www.hongkongairport.com/flightinfo-rest/rest/flights/past?date=YYYY-MM-DD&lang=en&cargo=false&arrival=true|false`
- Rolling **~91-day** window → the recorder Lambda (§8.2) stores every day in S3 from now on, and `scripts/backfill_hkia.py` pulls the whole current window once (182 requests, spaced ≥ 1 s apart).
- Actual times are inside the status string (`"At gate hh:mm"`, `"Landed hh:mm"`, `"Dep hh:mm"`), sometimes with a next-day marker; `terminal` may be empty; `statusCode` may be null; stands and gates are included. Parser in `flowcore/parse/hkia.py`, tested on saved fixtures.
- Days older than the window (e.g. Typhoon Noul, 25–27 Jul 2026) exist only in the trial's bucket (`raw/hkia/`, 2026-07-18 onwards). Copy them with the same key format if the hackathon rules allow pre-collected data (§8.9).
- Check in M2 that the endpoint answers from AWS (Lambda IPs); if blocked, run the recorder from a laptop cron and log it in `docs/decisions.md`. **Checked 2026-11-11: it does.** Out-of-window dates return HTTP 400 "out of valid range". One response can hold several date blocks; group flights by each block's `date`.

### 7.3 OAG (hackathon free tier) — `flowcore/sources/oag.py`

- Auth header `Subscription-Key: <key>`. Flight Info base `https://api.oag.com/flight-instances/` with query `version=v2`.
- **Limits per account, per 30 days:** Flight Info **1,000 requests, 10 results per request**; Connections **shares** that quota; Master Data 100 requests, 1 result each. Budget guard default **800** (`OAG_MAX_CALLS`).
- **Mandatory:** `DepartureDateTime` or `ArrivalDateTime`, plus `CarrierCode` or `DepartureAirport`/`ArrivalAirport`. `CodeType=IATA` must be sent whenever a carrier or airport is given (HTTP 400 without it, checked 2026-11-14; the client adds it). Default `Codeshare=OPERATING`.
- **`Content`:** blank = schedules · `STATUS` = latest status · `STATUSDETAILED` = every status update during the flight (how the estimated arrival moved) · `SEATS` = seat capacity by cabin (capacity, not free seats).
- **Connections URL:** copy it from the portal's "Try it" page into `OAG_CONNECTIONS_URL`; don't guess it.
- **Keys:** one free account per teammate. The portal issues **one key per product**: Flight Info → `/flow/oag-key-<profile>`, Connections → `/flow/oag-connections-key-<profile>` (Master Data is not used, so not stored). Profiles: `dev` (development) and `demo` (deployed app only); `OAG_KEY_PROFILE=dev|demo` selects. Because Flight Info and Connections share one quota, the ledger counts both against the account (identified by its Flight Info key).
- **Use OAG for:** the hero's inbound/outbound with `STATUSDETAILED` (the only OAG data the app needs: estimated times as they were published) and the M2 questions. `SEATS` gives aircraft **capacity**, not free seats, so free seats stay ASSUMED (`config/policy.yaml`); Connections is optional (later CX flights to the same city come from HKIA departures); Master Data is not used (100 calls/month, 1 result each; keep reference tables in the repo). **Use HKIA for whole days.** Target < 150 OAG calls in total.
- Alerts, flight tracker and the MCP server are **not** available: poll Flight Info for gate changes.
- **Answered in M2 (2026-11-11, see `docs/api_check.md`):** response `{data: [...], paging: {limit, totalCount, totalPages, next}}`;
  `next` is a full URL with an `After=` cursor (10 records per page: one day of CX arrivals at HKG = 257 flights = 26 calls, so
  query specific flights, not whole days). History: 2026-10-14 (4 weeks back) still returns full `statusDetails`.
  Estimated/actual times live in `statusDetails[]` (≈ 29–32 updates per flight, each with `updatedAt`, **not sorted**):
  `arrival.estimatedTime.{onGround,inGate}.{local,utc}`, `arrival.actualTime.{onGround,inGate}`, and
  `departure.{estimatedTime,actualTime}.{outGate,offGround}`, plus `*Timeliness`/`*Variation`; `state` ∈ Scheduled, OutGate,
  InAir, Landed, InGate. `SEATS` adds `seatingCapacity.predicted.{firstClass,businessClass,premiumEconomyClass,economyClass,totalSeats}`
  (capacity, not free seats). Date-only `ArrivalDateTime`/`DepartureDateTime` (`YYYY-MM-DD`) works.

### 7.4 Google Routes (Gate Planner) — `flowcore/sources/google_routes.py`

- `POST https://routes.googleapis.com/directions/v2:computeRoutes`, headers `X-Goog-Api-Key` (SSM `/flow/google-routes-key`) and `X-Goog-FieldMask: routes.duration,routes.staticDuration,routes.distanceMeters`.
- Driving: `travelMode: DRIVE`, `routingPreference: TRAFFIC_AWARE_OPTIMAL`, future `departureTime` (RFC 3339), `trafficModel: PESSIMISTIC` (upper estimate, historical) and `BEST_GUESS` (typical, includes live traffic near now). Traffic models are marked experimental and billed at a higher rate.
- Transit: `travelMode: TRANSIT` (no `routingPreference`/`trafficModel`); or Airport Express ASSUMED 24 min from Hong Kong Station, every 10 min.
- Destination: address string `"Hong Kong International Airport Terminal 1"`. Cache key rounds `departureTime` to 15 min.
- Google key comes from your own GCP project (Routes API enabled, billing on). If the team has no key, Gate Planner uses cached responses + the Airport Express fallback.

### 7.5 Synthetic layer (always labelled SYNTHETIC) — `research/flowresearch/synth.py`

- **Connections:** CX inbound → CX outbound at HKG, scheduled gap 50–240 min, plausible routing (e.g. Europe/N. America ↔ SE Asia/Oceania/N. Asia), weighted towards realistic gaps.
- **Passengers per arrival** (amended 2026-11-14): seats on that aircraft (type REAL from OAG, layout ASSUMED in `data/reference/aircraft_seats.yaml`) × Cathay's published passenger load factor (REAL) × HKG transfer share (REAL, derived from AAHK figures). Each party's cabin follows the aircraft's cabin split; its onward flight is drawn among plausible Cathay departures 50–240 min later, tighter gaps less often. Seat row, group share, assistance share and loyalty tier are ASSUMED mixes in `research/flowresearch/synth.py`. The scenario README states the sources and the known limits.
- **Preferences:** `earliest_arrival` | `keep_cabin` | `rest_first` | unset. Seeded; `is_synthetic=true` on every row.

### 7.6 Evidence (`data/evidence.json`, built by `research/flowresearch/build_evidence.py`)

Each item `{id, value, unit, label, source, note}`, computed **from fresh data** by the research pipeline; never typed in or
seeded from elsewhere. The panel needs:
- How often tight CX→CX connections (50–89 min scheduled, gate close 15 min before departure, cancellations excluded) break:
  normal days vs labelled disruption days (REAL flights, ASSUMED transfer times, SYNTHETIC passengers).
- How far away the next Cathay flight to the same city is after a miss (median hours, normal days; REAL).
- Policy simulation on the scenario day (SIMULATED): missing passengers with an approved plan before landing under
  TODAY / FLOW / AURA-style auto-rebook, and wrong bumps (moved off a flight they would have made).
- Published context figures only with a citation in `source`.

---

## 8. AWS setup (exact)

### 8.1 Accounts and local tools (M0, done by a human)

1. **Region:** `ap-southeast-1` (Singapore) for everything. Set `AWS_REGION=ap-southeast-1`.
2. **Local tools:** AWS CLI v2, Node 20+, Docker Desktop (running), uv, Python 3.12.
3. **Credentials:** `aws configure sso --profile flow` (IAM Identity Center) or, for a personal account, an IAM user with access keys under `--profile flow`. Then `export AWS_PROFILE=flow` and check `aws sts get-caller-identity`. Never use the root user's keys.
4. **No CDK bootstrap and no budget on the hackathon account** (amended 2026-11-14, Alex). Its permission set denies inline role policies (`iam:PutRolePolicy`), deleting or editing roles and policies, and everything under billing. `cdk bootstrap` needs the first, so it is not run: stacks deploy with the caller's own credentials (`CliCredentialsStackSynthesizer`), and `flow-data` creates the staging bucket and image repository. Cost tracking stays with the organisers. Rules for every stack are in `infra/flow_infra/common.py` and §17.3.10.

### 8.2 CDK stacks (`infra/`, Python, `aws-cdk-lib` v2)

Stack names use the context value `prefix` (default `flow`). Context defaults in `cdk.json`: `prefix=flow`, `oag_key_profile=demo`. Pass overrides with `-c key=value`.

**`flow-data` (FlowDataStack)**
- S3 bucket, name `flow-data-<account>-<region>`: `BlockPublicAccess.BLOCK_ALL`, `BucketEncryption.S3_MANAGED`, `enforce_ssl=True`, versioning off, **`RemovalPolicy.RETAIN`** (HKIA history can't be re-downloaded once it ages out).
- Prefixes (convention, not resources): `raw/{hkia,oag,google}/`, `ledger/{oag,google}/`, `processed/`, `scenarios/`, `models/`, `evidence/`, `state/`.
- Staging for deploys (instead of `cdk bootstrap`): S3 bucket `flow-assets-<account>-<region>` (same settings, objects expire after 30 days) and ECR repository `flow-app` (keeps 5 images), both `RETAIN`.
- Deployed with plain CloudFormation from the synthesised template (`make deploy-data`), because `cdk deploy` needs the staging bucket this stack creates. Deploy it first.
- Outputs: `BucketName`, `AssetsBucketName`, `AppRepositoryName`.

**`flow-recorder` (FlowRecorderStack)**: fixes the old macOS launchd recorder
- Lambda `<prefix>-hkia-recorder`: Python 3.12, ARM64, 256 MB, timeout 120 s, env `BUCKET`, code `infra/lambda/hkia_recorder/handler.py` (stdlib `urllib` + runtime `boto3`; no extra packages).
- Behaviour: for each date in the event's `dates` list, or by default **yesterday and the day before (HKT)**, and for `arrival` in `[true, false]` with `cargo=false`: skip if `raw/hkia/past_<date>_<arr|dep>.json` exists; else GET the HKIA URL (§7.2) with a `User-Agent`, and write the **same envelope as §7.1**. Sleep 1 s between requests. Log counts.
- EventBridge rule `cron(0 18 * * ? *)` (UTC = 02:00 HKT daily) → Lambda.
- Role: one retained role with managed policies only: `AWSLambdaBasicExecutionRole` plus `s3:GetObject` and `s3:PutObject` on `raw/hkia/*` and `s3:ListBucket` on the bucket. No delete.
- Outputs: `RecorderFunctionName`.

**`flow-app` (FlowAppStack)**
- VPC: 2 AZs, **public subnets only, `nat_gateways=0`**.
- ECS cluster + `ecs_patterns.ApplicationLoadBalancedFargateService`:
  - `runtime_platform`: Linux / **ARM64**; `cpu=1024`, `memory_limit_mib=2048`.
  - `desired_count=1`, **`min_healthy_percent=0`, `max_healthy_percent=100`** (never two tasks), `circuit_breaker=DeploymentCircuitBreaker(rollback=True)`, `assign_public_ip=True`, task subnets public, `health_check_grace_period=60 s`.
  - Image: `ecs.ContainerImage.from_asset(<repo root>, file="Dockerfile", platform=Platform.LINUX_ARM64, exclude=[".git", "web/node_modules", "data/raw", "research", "infra/cdk.out", ".venv"])`.
  - Container port 8000; log driver to CloudWatch with 1-week retention.
  - Environment: `AWS_REGION`, `FLOW_BUCKET`, `OAG_KEY_PROFILE`, `FLOW_PARAM_PREFIX=/flow`, `OFFLINE=0`, `FLOW_REPO_ROOT=/app`.
  - Target group health check path `/api/health`; ALB attribute `idle_timeout.timeout_seconds=3600` (long-lived WebSockets).
- Roles: created in `flow-data` (the account cannot delete roles, and this stack is destroyed often), managed policies only. Task role: `s3:GetObject`, `s3:PutObject` and `s3:ListBucket` on the data bucket; `ssm:GetParameter(s)` on `parameter/flow/*`; `kms:Decrypt` via SSM; plus spare permissions fixed at creation (`s3:DeleteObject` on `state/*` only, invoke the recorder Lambda, ECS Exec channels, CloudWatch metrics in namespace `Flow`). Execution role: `AmazonECSTaskExecutionRolePolicy`.
- CloudFront distribution in front of the ALB: origin `origins.LoadBalancerV2Origin(alb, protocol_policy=HTTP_ONLY)`, `viewer_protocol_policy=REDIRECT_TO_HTTPS`, `allowed_methods=ALLOW_ALL`, `cache_policy=CachePolicy.CACHING_DISABLED`, `origin_request_policy=OriginRequestPolicy.ALL_VIEWER`. WebSockets pass through CloudFront.
- Outputs: `AppUrl` (`https://<distribution domain>`), `AlbUrl`.
- **WebSocket keep-alive:** the server sends `{"type":"ping"}` every 20 s; the web client reconnects with backoff and re-fetches state on reconnect.

### 8.3 Secrets (SSM Parameter Store, SecureString)

CloudFormation can't create SecureString values, so `scripts/put_secrets.sh` prompts for each value (hidden input) and runs `aws ssm put-parameter --name <name> --type SecureString --overwrite --value <value>`:

| Parameter | Used by |
|---|---|
| `/flow/oag-key-dev` | OAG Flight Info: laptops, research, `check_apis.py` |
| `/flow/oag-connections-key-dev` | OAG Connections: laptops, research |
| `/flow/oag-key-demo` | OAG Flight Info: deployed app only |
| `/flow/oag-connections-key-demo` | OAG Connections: deployed app only |
| `/flow/google-routes-key` | Gate Planner |

`flowcore.aws.get_secret(name, env_var)` reads the env var first (e.g. `OAG_KEY_DEV`), then `/flow/<name>`; returns `None` if missing.

### 8.4 Environment variables (`.env.example`, names only)

`AWS_PROFILE=flow` · `AWS_REGION=ap-southeast-1` · `FLOW_BUCKET=` (from `flow-data` output) · `FLOW_PARAM_PREFIX=/flow` · `OFFLINE=0` · `OAG_KEY_PROFILE=dev` · `OAG_MAX_CALLS=800` · `OAG_CONNECTIONS_URL=` · `GOOGLE_MAX_CALLS=300` · optional overrides `OAG_KEY_DEV`, `OAG_KEY_DEMO`, `OAG_CONNECTIONS_KEY_DEV`, `OAG_CONNECTIONS_KEY_DEMO`, `GOOGLE_ROUTES_KEY`.

### 8.5 Dockerfile (repo root)

- Base `python:3.12-slim`; `ENV FLOW_REPO_ROOT=/app PYTHONUNBUFFERED=1`; `WORKDIR /app`.
- `pip install -r backend/requirements.lock` (exact versions exported from `uv.lock` by `make lock-backend`), then `pip install --no-deps ./flowcore`.
- Copy `backend/app/` (including `static/` built by `make build-web`), `config/` and `data/` (`.dockerignore` keeps out `raw/`, `processed/`, `state/`, `models/`).
- Models: downloaded from S3 at startup via `flowcore.models` into `/app/data/models/` (not baked in).
- `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]`.
- Built for `linux/arm64` (native on Apple Silicon; on Intel/AMD machines Docker Desktop builds it with emulation, slower but works).

### 8.6 `scripts/check_apis.py` → `docs/api_check.md` (M2)

Each check prints PASS/FAIL and writes findings. Live calls go through the cache and ledger.

1. **AWS:** `sts get-caller-identity`; put + get + delete `s3://$FLOW_BUCKET/healthcheck.txt`; read `/flow/oag-key-dev` exists (don't print it).
2. **HKIA:** yesterday's arrivals and departures: flight count, CX count, 5 example status strings, stand/gate fill rate. Also invoke the recorder Lambda once and confirm the files appear in S3 (answers "does HKIA answer AWS IPs?").
3. **OAG (≤ 3 calls, dev key):** (a) `ArrivalAirport=HKG, CarrierCode=CX, ArrivalDateTime=<yesterday>, Content=STATUSDETAILED`; (b) same for `2026-10-14` (how far back history goes); (c) one `SEATS` call for HKG→SIN tomorrow. Write: top-level keys, the full field list of one record, **which fields hold estimated/actual times**, how many status updates one flight has, how paging works (next link? page parameter? total count?), and calls used so far.
4. **Google Routes (2 calls):** Central → HKIA T1, departure in 2 h, `PESSIMISTIC` and `BEST_GUESS`: both durations and `staticDuration`.

### 8.7 Makefile targets (keep all working)

```
make setup             # uv sync --all-packages; cd web && npm ci (if web exists)
make aws-whoami        # aws sts get-caller-identity
make cdk-bootstrap     # not used on the hackathon account (§8.1.4); prints why
make diff-data         # cdk diff flow-data (same for diff-recorder)
make deploy-data       # synth + CloudFormation deploy of flow-data (first)
make deploy-recorder   # cdk deploy flow-recorder
make secrets           # scripts/put_secrets.sh
make backfill-hkia     # scripts/backfill_hkia.py (whole 91-day window via the Lambda)
make data-down         # aws s3 sync s3://$FLOW_BUCKET/{raw,processed,scenarios} data/...
make data-up           # aws s3 sync data/{processed,scenarios} s3://$FLOW_BUCKET/...
make check-apis        # scripts/check_apis.py → docs/api_check.md
make dev               # uvicorn --reload :8000 + vite :5173 (proxy /api and /ws)
make test              # pytest + vitest
make contract          # export OpenAPI + regenerate web/src/api/types.ts
make build-web         # npm run build, copy web/dist → backend/app/static
make deploy            # build-web, then cdk deploy flow-app (prints AppUrl)
make logs              # aws logs tail on the app's log group --follow
make demo              # local full demo; OFFLINE=1 make demo for no network
make destroy-app       # cdk destroy flow-app (keeps data + recorder; do this when not testing)
```

### 8.8 Cost and teardown

Rough cost while `flow-app` is up: Fargate (1 vCPU ARM, 2 GB) + ALB, roughly **US$1–2 per day**; CloudFront, S3, Lambda and SSM are pennies at our volume. **Run `make destroy-app` when not testing** and redeploy with `make deploy` (about 5–10 min). Never destroy `flow-data`.

### 8.9 Moving to the hackathon account on Saturday

Same commands with the hackathon credentials: new profile → `cdk-bootstrap` → `deploy-data` → copy data from the personal bucket (`aws s3 sync s3://<personal>/... ./data/` with the `flow` profile, then `aws s3 sync ./data/ s3://<hackathon>/...` with the hackathon profile; **processed/scenarios/models/evidence only**, not raw OAG) → `secrets` → `deploy`. Check the hackathon account's region first; switch `AWS_REGION` if needed.

---

## 9. Research (`research/`) and models

- `research/` holds training, backtests and the evidence pipeline. It reads from S3 (`raw/`, `processed/`) and writes to S3 (`processed/`, `models/`, `evidence/`) plus `data/evidence.json`.
- **Model artifacts:** `s3://$FLOW_BUCKET/models/<name>/<version>/` containing the model file (e.g. LightGBM `.txt`), `meta.json` (`{name, version, trained_at, train_dates, features, metrics, label}`) and the training command. `flowcore/models.py` reads `config/models.yaml` (`{name: version}`, committed) and downloads the pinned versions at app startup. The app never trains.
- **Build the analysis on `flowcore`** (same parser, same engine as the app): dataset → backtests → break rates → policy simulation → models → evidence, from fresh data. `research/README.md` lists the command that reproduces every number in `evidence.json`.
- **For Saturday:** the competition repo holds only the app. Research results enter as data (`evidence.json`, scenario files, model artifacts in S3) only if the organisers allow pre-prepared data; otherwise the training script is rewritten on the day (LightGBM on ~80 days trains in seconds).

---

## 10. API contract

FastAPI generates `contracts/openapi.json` (`make contract`). Times are ISO-8601 with `+08:00`. Every object carrying numbers has `labels: {field: "REAL"|"ASSUMED"|"SYNTHETIC"|"SIMULATED"}`.

### 10.1 Core schemas (`backend/app/schemas.py`)

```python
Zone = Literal["SAFE", "AT_RISK", "WONT_MAKE"]
ConnState = Literal["MONITORING", "BACKUP_HELD", "DRAFT_PENDING", "OFFERED",
                    "PASSENGER_CHOSE", "MADE_ORIGINAL", "REBOOKED"]

class FlightRef(BaseModel):
    flight: str; origin: str; dest: str
    sched: datetime; est: datetime | None; actual: datetime | None   # est/actual only if known at t
    stand: str | None; gate: str | None
    status: str           # "Scheduled" | "Airborne" | "Landed" | "At gate" | "Departed" | "Cancelled"
    labels: dict[str, str]

class TimeRange(BaseModel):
    p10: datetime; p50: datetime; p90: datetime

class Driver(BaseModel):
    key: str              # "inbound_delay" | "remote_stand" | "far_gate" | "wave_load" | "deplane_row"
    minutes: float; text: str

class Hold(BaseModel):
    hold_id: str; flight: str; dep: datetime; cabin: str; seat: str | None; expires_at: datetime

class ConnectionStatus(BaseModel):
    connection_id: str; pid: str; t: datetime
    inbound: FlightRef; outbound: FlightRef; gate_close: datetime
    ready_at_gate: TimeRange
    minutes_available: int              # gate_close − p50 arrival at gate ("Time you'll have")
    minutes_needed: tuple[int, int]     # transfer p10..p90 ("Time you'll need 25–40 min")
    p_miss: float; zone: Zone; state: ConnState
    drivers: list[Driver]; backup_hold: Hold | None; expedite_offered: bool
    labels: dict[str, str]

class Option(BaseModel):
    option_id: str
    kind: Literal["ORIGINAL_EXPEDITE", "ALT_FLIGHT", "OVERNIGHT"]
    title: str; flight: str; dep: datetime; final_arrival: datetime
    cabin: str; seat: str | None
    guaranteed: bool      # False for ORIGINAL_EXPEDITE ("if you make the gate")
    extras: list[str]; approved: bool
    labels: dict[str, str]

class Draft(BaseModel):
    draft_id: str; connection_id: str; pid: str; passenger_name: str; cabin: str
    group_size: int; assistance: bool; tier: str
    p_miss: float; option: Option; rationale: str
    status: Literal["PENDING", "APPROVED", "REJECTED"]
```

Also `Passenger`, `Trip`, `ReplayState {scenario_id, t, speed, playing}`, `WaveSummary`, `PlannerRequest`/`PlannerResult`, `ImpactMetric`, `Health {ok, version, offline, bucket, scenario}`.

### 10.2 Endpoints

| Method | Path | Returns |
|---|---|---|
| GET | `/api/health` | `Health` |
| GET | `/api/scenarios` | scenario ids + titles |
| POST | `/api/replay/load` `{scenario_id}` | `ReplayState` |
| POST | `/api/replay/control` `{action: play\|pause\|seek\|speed, t?, speed?}` | `ReplayState` |
| GET | `/api/replay/state` | `ReplayState` |
| GET | `/api/passengers/{pid}/trip` | `Trip` |
| GET | `/api/passengers/{pid}/protect` | `ConnectionStatus` |
| GET | `/api/passengers/{pid}/options` | `list[Option]` sorted by the passenger's preference |
| POST | `/api/passengers/{pid}/choose` `{option_id}` | `ConnectionStatus` |
| GET | `/api/staff/wave?from=&to=` | `WaveSummary` + `list[ConnectionStatus]` |
| GET | `/api/staff/drafts?status=PENDING` | `list[Draft]` |
| POST | `/api/staff/drafts/{id}` `{decision: approve\|reject, note?}` | `Draft` |
| POST | `/api/staff/drafts/approve-batch` `{ids}` | `list[Draft]` |
| POST | `/api/planner/plan` | `PlannerResult` |
| GET | `/api/impact` | `list[ImpactMetric]` |
| WS | `/ws?role=passenger&pid=…` or `/ws?role=staff` | `{type, t, payload}`: `clock`, `connection_update`, `draft_update`, `options_update`, `notification`, `ping` |

Every endpoint and WS message type has a fixture in `contracts/fixtures/`.

---

## 11. Engine and policy (in `flowcore/engine/` and `backend/app/policy/`)

All parameters live in `config/engine.yaml` / `config/policy.yaml` with a comment saying where the number comes from (`REAL: derived from …` or `ASSUMED: …`). Every stochastic function takes a seed.

### 11.1 Time to gate (Connection Protect)

N samples per connection (default 2,000; vectorised; < 1 s for 500 connections):

```
ready_at_gate = inbound_at_gate + deplane + (bus if remote stand) + transfer_security + walk
gate_close    = outbound_departure − 15 min          (Cathay gate close since 1 Jun 2026)
p_miss        = mean(ready_at_gate > gate_close)
```

| Component | Before take-off | After take-off | Label |
|---|---|---|---|
| Inbound at-gate time | sched arr + origin departure delay (once departed) + residual from history (by origin/hour) | **OAG estimated arrival** (from `STATUSDETAILED`, as known at *t*) or HKIA landed time, + taxi-in | REAL; taxi-in ASSUMED until fitted (default N(8, 3) min, floor 3) |
| Stand type | historical remote-stand share for that arrival | HKIA stand when known | REAL |
| Deplane | F/J ~5 ± 2 min, W ~9 ± 3, Y 8–18 by row | same | ASSUMED |
| Bus (remote stand) | +10 ± 3 min | same | ASSUMED |
| Transfer security | 5–20 min, rising with arrival-wave size | same | ASSUMED |
| Walk | zone-to-zone distance (`data/reference/hkg_zones.yaml`) ÷ N(1.2, 0.2) m/s; Midfield adds the train | same | ASSUMED |
| Outbound departure | sched + predicted delay (empirical or LightGBM; OAG est. dep when available); a late outbound helps | same | REAL history |

**Calibration anchor:** for a typical CX→CX connection, our transfer-time P10–P50 should sit near the official minimum connecting time from OAG Connections. Log the comparison in `docs/decisions.md`.

Outputs: `ready_at_gate` P10/P50/P90; `minutes_needed` = transfer P10–P90; `drivers` = 2–3 components adding the most minutes above typical, as plain sentences.

**Zones** (thresholds in `config/policy.yaml`, **never shown in the UI**): `SAFE` below `tau_watch` (0.20), `AT_RISK` up to `tau_act` (0.70), `WONT_MAKE` above; hysteresis ±0.05. **Baselines** kept callable: `R0` fixed 38-min rule (deplane 8 + transfer 15 + gate close 15) and `R1` = R0 + predicted outbound delay.

### 11.2 Policy state machine

```
MONITORING ──(AT_RISK)──► BACKUP_HELD ──(WONT_MAKE)──► DRAFT_PENDING ──(staff approve)──► OFFERED
    ▲                         │                              │ (reject → BACKUP_HELD, logged)
    └──(SAFE for 2 ticks)─────┘ release hold                 ▼
                                                     PASSENGER_CHOSE ──► MADE_ORIGINAL | REBOOKED
```

- **Backup hold:** on `AT_RISK`, hold the best alternative seat per preference; expires at original gate close + 30 min; released on `MADE_ORIGINAL` or a return to `SAFE`.
- **Drafts:** on `WONT_MAKE`, create a `Draft` from the held seat (or best available) with a template rationale.
- **No answer by gate close and not boarded:** convert the held seat (the only automatic move, and only after the miss).
- **`MADE_ORIGINAL`** comes from the replay's ground truth.

### 11.3 Seats and allocation

- Alternatives: later CX flights to the same destination that day/next morning (OAG/HKIA schedules); oneworld via OAG Connections optional.
- Free seats (amended 2026-11-14): seats per cabin for the flight's aircraft × (1 − Cathay's published load factor), i.e. the seats left unsold at departure on average; `policy.yaml` defaults (F1/J3/W2/Y6, ASSUMED) only when the type is unknown. No separate depletion over time: the load factor already describes departure. Track peak concurrent holds.
- Missed with no seat held (every later flight full): flagged `needs_manual_rebooking` for staff; never rebooked automatically.
- Competing passengers: **CP-SAT**, binary `x[i,a]`, maximise preference-weighted value; constraints: capacity per (flight, cabin), groups together or not at all, assistance first, ≤ 1 hold per passenger. Also compute greedy first-come and log both.

### 11.4 Expedite (fast-track / escort)

Offered to `AT_RISK` passengers where it lowers `p_miss` most; capacity ASSUMED (4 escorts per 30 min); effect ASSUMED (transfer −6 ± 2 min). Labelled ASSUMED everywhere: not proven to save connections.

### 11.5 Rationale template

`"{name} ({cabin}, {group}): {p_miss:.0%} likely to miss {out_flt}. {driver_text}. Backup held on {alt_flt} {alt_dep:%H:%M}, arrives {alt_arr:%H:%M}. Prefers {pref}."` A test asserts every number and flight number in the rationale equals the draft's fields.

---

## 12. Gate Planner (`flowcore/engine/gate_planner.py`)

Input: origin, flight + date, checked bags, checked in online, HK resident, mode (car/taxi or Airport Express), buffer (`relaxed` P95 / `balanced` P85 / `tight` P70).

```
door_to_gate = road (Routes PESSIMISTIC upper; BEST_GUESS typical) + check-in/bag drop (0 if online + no bags; else ASSUMED queue by hour)
             + security & immigration (residents e-Channel ASSUMED ~5 min; visitors ≤ 15 min per ImmD pledge, 95%) + walk (zone matrix)
deadline     = bag drop close (dep − 60 min) if checked bags, else gate close (dep − 15 min)
leave_by     = deadline − door_to_gate at the chosen percentile
```

Output: leave-by, per-step breakdown with labels, typical vs upper, nudges. Re-plans on a gate change (OAG/HKIA at *t*) or a road-estimate change. A later departure only moves leave-by once the airline has published the new time.

---

## 13. Milestones (no timebox; in order; next only when the current DoD passes)

> **CURRENT MILESTONE: M10** (offline + rehearsal). Passed on 2026-11-14: M0–M3; M4 in reduced form (no trained model, `docs/decisions.md`); M5–M9 (screens, live replay, closed loop with golden tests and `make e2e`, Gate Planner, impact panel). Open: the phone + laptop check on the deployed URL, three rehearsals, the backup recording, `make destroy-app` when idle. Update when a DoD passes, and log the time taken in `docs/build_log.md`.

**Deploy early:** from M3 onwards, run `make deploy` at the end of every milestone and check the `AppUrl` on a phone.

| # | Milestone | Definition of done |
|---|---|---|
| **M0** | Accounts + local setup | §8.1 done; `make setup` and `make aws-whoami` work; repo skeleton per §6 with empty packages; `make test` green (no tests yet is fine). |
| **M1** | Data infrastructure | `flow-data` and `flow-recorder` deployed; `make secrets` stored all available keys; `flowcore` config/aws/cache/sources written with tests (moto for S3/SSM); `make backfill-hkia` stored every day still in the HKIA window; raw HKIA days older than the 91-day window copied from the trial bucket if allowed (§7.2, §17.4). |
| **M2** | API check | `make check-apis` passes and `docs/api_check.md` answers every question in §8.6, especially **OAG's estimated-arrival fields, paging and history depth**. OAG calls used ≤ 10. |
| **M3** | Deployed skeleton | `flow-app` deployed; `AppUrl` on a phone shows `/api/health` and a test page that receives WebSocket `clock` messages every 5 s for 10+ minutes without dropping. |
| **M4** | Research | `research/` builds `processed/flights.parquet` from S3, computes the evidence (§7.6) using `flowcore.engine`, uploads models to `models/`, writes `evidence.json`; `research/README.md` lists the commands. |
| **M5** | Scenario + slice on fixtures | `data/scenarios/<id>/` built; Mei chosen per §3; `/app` shows the journey strip and the Connect screen (Plan A / Plan B) → staff approval → switch → Plan B, from `contracts/fixtures/`; `/staff` shows a wave and drafts from fixtures; matches `docs/design/`. Deployed. |
| **M6** | Engine + replay live | Replay clock drives the engine; Mei's status changes on schedule; `/app` updates over WebSocket; leakage test passes. Deployed. |
| **M7** | Closed loop | Holds, drafts, approve (single + batch), choose, release; both screens update within 1 s; **`test_demo_path.py` and `test_nonnegotiables.py` pass** (no merge if they fail from here on). Deployed and tested phone + laptop together. |
| **M8** | Gate Planner | Planner screen with breakdown and leave-by; Routes responses cached; gate-change re-plan works in replay. |
| **M9** | Impact + shell | `/impact` renders `evidence.json` with labels + live replay stats; Flow shell with five stages. |
| **M10** | Offline + rehearsal | `OFFLINE=1 make demo` runs the full story with Wi-Fi off; demo script run 3× on the deployed URL without failure; backup screen recording saved; `make destroy-app`. `docs/build_log.md` complete. |

---

## 14. Build log

Keep `docs/build_log.md` updated. Per milestone: **wall-clock time** and who/which agent did it; **what the agent got wrong** and the instruction that fixed it (collect these as proposed additions to §17); **data and AWS surprises** (OAG fields, quotas, IAM errors, deploy times); **what we'd cut or do first next time**.

---

## 15. Working conventions for agents

1. **Plan, then code** for anything over ~50 lines (plan in chat or `docs/decisions.md`).
2. **Infra change needed?** Stop and ask (§6). Contract changes go through `schemas.py` and `make contract`.
3. **Contract first.** Frontend uses generated types and fixtures only.
4. **Small commits, merged often**; rebase before merging; `make test` before every merge.
5. **Config, not constants**: any meaningful number goes in YAML with a comment and a label.
6. **Determinism**: seeds everywhere; replay reproducible.
7. **Tests:** parsers on saved real fixtures; engine on hand-computed tiny cases; AWS code with `moto` (never real AWS in tests); non-negotiables explicitly; one Playwright demo test.
8. **AWS changes go through CDK only.** No console click-ops except §8.1 (SSO). If you had to click something, write it in `docs/decisions.md`.
9. **UI copy:** sentence case, plain English, the Figma screens' wording ("Both plans are ready", "Keep both plans", "Switch to …", "Nothing changes unless you choose").
10. **Don't over-build** (§16). **When unsure, ask.** Never trade a non-negotiable for speed.

## 16. Out of scope

Real bookings, payments, real passenger data, calls to Cathay/Amadeus systems, user accounts/auth, custom domains, push notifications to real phones, native apps, multi-airport support, a database server, CI/CD pipelines (deploy from a laptop with `make deploy`).

---

## 17. Rules learned in the trial (read before M0)

A full trial build (one agent, 2026-11-11 to 11-13) hit every problem below once. Each line is the rule that
fixed it. Research results from the trial are deliberately **not** here (§9: redo on fresh data).

### 17.1 Team, agents and git
1. Decide on day one who owns what and whether the agent may commit to `main`. Unanswered, the first session stalls. *Decided 2026-11-14:* one person owns all the code, with one agent; no roles (§6).
2. Add Claude Code permission rules for `make deploy*` and `make destroy-app` before starting: the auto-mode classifier blocks infrastructure applies otherwise.
3. Check the test command's **own** exit code before committing; never `pytest … | tail && git commit` (that is `tail`'s exit code).
4. Assert every scripted edit (sed/python replace) matched; several silently changed nothing. Check build exit codes before trusting screenshots (a failed build leaves a stale `dist/`).
5. zsh doesn't word-split `$VAR` lists: use arrays or `xargs`. Test every documented command exactly as written.
6. Port formulas verbatim from their source and cite it; never approximate a constant or divisor.
7. Never type a number into UI copy, string props included; the digit guard only sees JSX text.

### 17.2 Versions and tooling
1. Pin every CLI and library to a version **≥ 2 weeks old**, and pin CLI and lib together: aws-cdk CLI 2.1146.1 with aws-cdk-lib 2.274.0 worked; a fresh release failed to download (ETARGET) and a newer lib broke the older CLI.
2. Pin scikit-learn for model pickles (1.9.1 in the trial); the app must unpickle with the same version, so the model class lives in `flowcore`.
3. pytest: default import mode, no `__init__.py` in test folders, **test file names unique across packages** (prefix with the package, e.g. `test_flowcore_cache.py`); `norecursedirs` skips `infra/cdk.out`, `node_modules`, `dist`.
4. Upgrade the AWS CLI to v2 arm64 native before starting.
5. Python from python.org may have no CA bundle (`CERTIFICATE_VERIFY_FAILED`): test clients use `certifi`. Read the error text before blaming the infrastructure.

### 17.3 AWS and CDK
1. SSO config: `sso_registration_scopes = sso:account:access` (a bare `sso` gives `invalid_scope` on login).
2. Run `cdk bootstrap` **outside** `infra/` (inside, it synthesises the stack-less app and fails).
3. `cdk deploy` asks for IAM approval and `cdk destroy` asks y/n, which an agent can't answer: Makefile variables `CDK_APPROVAL` (default `broadening`; `never` only after the human approved the shown `cdk diff`) and `CDK_DESTROY_FLAGS`.
4. Never `grant_read_write` on `raw/`: use `grant_read` + `grant_put` and a test asserting no `s3:DeleteObject*`. Read the IAM table in every `cdk diff`.
5. ALB target-group `deregistration_delay` = 10 s from the first deploy (default 300 s gave 5+ minutes of 503 on every single-task deploy). Never deploy during a demo.
6. Deploy times: data stack ~30 s, recorder ~2 min, app ~8.5 min (CloudFront is most of it). Destroy the app stack when idle (`flow-app` ≈ US$1–2/day).
7. Never return resource names that embed the account ID (bucket names) from a public endpoint like `/api/health`; mask them and test it.
8. Mutable state keys (replay snapshots in S3 `state/`) are per environment (`FLOW_STATE_ENV` = local | cloud | e2e); a laptop snapshot once leaked into the cloud replay.
9. AWS Budgets email subscribers get no confirmation mail; verify the budget and recipient in the console instead.
10. Read the account's permission set before the first deploy (`aws iam get-role-policy` on your own role). On the hackathon account: no inline role policies, no deleting or editing roles and policies, no billing. So: managed policies only, roles and policies `RETAIN`, permissions right on the first deploy, no constructs that create their own roles (auto-delete objects, log-retention custom resources), no `cdk bootstrap`. A test asserts the templates contain none of these.

### 17.4 External APIs and data
1. Run `make check-apis` in the first hour; it must print each API's error message, not just the status.
2. OAG issues **one key per product** (Flight Info, Connections, Master Data); Flight Info and Connections share the 1,000-call quota. One full day of CX arrivals is 26 pages: query specific flights, never whole days. `statusDetails[]` is not sorted by `updatedAt`; reveal each estimate only once replay time ≥ `updatedAt`. Pick the record with non-empty `statusDetails`. Mask letters as well as digits in identifiers in any report.
3. Store raw OAG responses only in S3; commit derived timelines only.
4. HKIA's window is exactly 91 days back from yesterday (older dates: HTTP 400 "out of valid range"). Start the recorder on day one. One response can hold several date blocks: group by each block's `date`. Store only 2xx **non-empty** bodies so a bad day is retried, not skipped forever. HKIA answers from Lambda IPs.
5. Google Routes traffic needs a **future** departure time: for a past replay day, ask for the same weekday and time next week and say so. After one key rejection, stop calling Google for the process (protects the ledger) and fall back to the Airport Express table.
6. Any seeded sample (normal-day pool, synthetic passengers) pins its data window, or results change as days are added.
7. Stands and gates are treated as known for the whole replay (HKIA has no assignment timestamps; ASSUMED). Delays stay strictly as-of t.

### 17.5 Backend, replay and tests
1. Profile the replay tick on the target CPU before the first demo: the 1-vCPU task ran at 20× instead of 60×. Cache per-party facts at load and draw transfer times once per scenario (they don't depend on t): 4× faster.
2. Golden tests first (`test_demo_path.py`, `test_nonnegotiables.py`): in the trial they found two real bugs before any UI existed.
3. Read intervals and env-dependent settings at app creation, not as module constants (a session fixture changed env vars process-wide).
4. Make: environment variables must beat `.env` for `OFFLINE` (`OFFLINE=1 make demo` was silently online).
5. Test WebSocket clients must drain their sockets like a browser, or they die with keepalive timeouts that look like server faults.
6. Playwright: one worker (specs share one backend and seek its replay); prefer role + exact-name selectors (text like "All" also matches "Approve all").
7. Vitest with Testing Library: add `afterEach(cleanup)`; auto-cleanup is off without `globals`, and a second render keeps the first in the DOM.
8. Seek fast-forwards in 5-minute engine steps; live play ticks every simulated minute.

### 17.6 Front end and design
1. Light-only pages: Tailwind `darkMode: "class"` (media dark mode fired leftover `dark:` variants in a dark-mode browser at 1:1 contrast).
2. Bundle fonts with `@fontsource` (works offline); keep `MotionConfig reducedMotion="user"`.
3. Figma MCP on a Starter plan allows very few calls a month: work from PNG exports plus 1–2 frame links; the trial frames had no Figma variables, so tokens come from text styles and sampled pixels (`docs/design/README.md`).
4. A design that shows numbers needs a data source per number, or a sample-data decision before the build (non-negotiables 6 and 10). Sample values are derived from real ones (e.g. bag times from real flight times) and checked for contradictions.
5. Wait for the replay clock before choosing which journey screen to show (the first render otherwise uses the wall clock).
6. Every source badge ≥ 11 px; AA contrast; visible focus ring; arrow keys in radio groups.

### 17.7 Build order and what to cut
- Order: AGENTS.md + permissions → AWS and keys → recorder + data → research and evidence (if allowed) → engine + replay + golden tests → staff console + phone → deploy → Gate Planner → impact → rehearsal.
- Trial timings: M0–M2 ≈ 2 h (mostly human console steps), M3 ≈ 1 h, M4 ≈ 1.5 h (≈ 30 min compute), M5–M7 ≈ 3 h, M8–M9 ≈ 1.5 h, M10 ≈ 0.5 h + rehearsals.
- Cut first: Gate Planner road leg (Airport Express fallback), animation polish.
- Never cut: the non-negotiable tests, staff approval before an option is offered, the passenger chooses, labels in every API payload.
