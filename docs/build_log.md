# Build log

Per milestone: wall-clock time, who/which agent, what went wrong and the rule that fixed it, data and AWS surprises (AGENTS.md §14). Propose new rules for AGENTS.md §17.

## M0: Accounts + local setup

- **When / who:** Sat 14 Nov 2026, started 17:36 HKT, Alex with Claude Code (one agent, no roles). Skeleton and
  first green `make test` took roughly half an hour (not timed exactly).
- **Done:** repo skeleton per §6 (uv workspace: `flowcore`, `backend`, `research`, `infra`), Makefile with every §8.7
  target (later-milestone targets are stubs that exit 1 and name their milestone), `.env.example`, `.gitignore`.
  `make setup` works; `make test` passes.
- **Not done (needs a person):** `make aws-whoami` fails because the `flow` SSO login has expired
  (`aws sso login --profile flow`). CDK bootstrap and the budget email (§8.1) are unconfirmed.
- **Versions:** `uv.lock` pins everything, and `exclude-newer = 2026-10-31` in the root `pyproject.toml` enforces the
  "at least two weeks old" rule (§17.2.1) at resolve time. aws-cdk CLI 2.1146.1 with aws-cdk-lib 2.274.0 synthesises cleanly.
- **Decision on `.env`:** Python reads `.env` itself with the real environment on top. The Makefile takes only a short
  list of non-secret names from `.env` using `?=`, so `OFFLINE=1 make …` wins and keys never pass through make (§17.5.4).

- **AWS surprises:** with no `.env`, `make aws-whoami` answered as another project's IAM user (the laptop's
  default credentials). AWS targets now require `AWS_PROFILE`. macOS ships GNU Make 3.81, which ignores `.SHELLFLAGS`,
  so `aws … | sed` exited 0 on a failed login; pipefail now sits on `SHELL`. *Proposed rules (§17.1/§17.3):* refuse AWS
  commands without an explicit profile; test every piped make recipe with a failing left side.
- **Hackathon account:** empty, not bootstrapped, role from an Identity Center permission set.

## M1: Data infrastructure

- **Done:** `flowcore` config, AWS helpers, cache and ledger, HKIA / OAG / Google Routes clients, the HKIA parser;
  `flow-data` and `flow-recorder` stacks and the recorder Lambda; `scripts/put_secrets.sh`, `backfill_hkia.py`,
  `data_sync.sh`. Tests use moto and a fake HTTP transport: no real AWS, no real keys, no network.
- **Waiting on a person:** SSO login, `BUDGET_EMAIL` in `.env`, approval of the `cdk diff` before each deploy, `make secrets`.
- **What the agent got wrong:**
  - OAG next-page links lost their `After=` cursor: httpx drops a URL's own query string when `params={}` is passed.
    A test caught it before any real call. *Proposed rule (§17.4):* pass `params=None`, not `{}`, when the URL already
    carries its query; test paging against a full next-page URL.
- **Data surprises (HKIA, real response for 2026-11-13, one request each for arrivals and departures):**
  - A day's file also holds a few flights scheduled on the day before or after whose actual time fell on that day
    (3 of 423 arrivals, 4 of 421 departures). The block `date` is the scheduled date. The same flight therefore appears
    in two files; the parser keeps one row per flight. *Proposed rule (§17.4):* deduplicate on (direction, scheduled
    time, operating flight) when reading several days.
  - Past days say "At gate hh:mm" for every arrival; there is no "Landed" time. Taxi-in cannot be fitted from HKIA
    past data; it needs OAG's on-ground and in-gate times, or stays ASSUMED.
  - `flight[0]` is the operating flight. 165 of 237 arrivals that carry a CX number are operated by Cathay; the rest
    are codeshares on other airlines (e.g. HK Express).
  - Multi-stop flights list several airports: arrivals origin-first, departures next-stop-first.
  - `statusCode` is always null; arrival `terminal` is always empty; one cancelled flight each way has no stand or gate.
- **Deployed (18:34–18:37 HKT by the stacks' creation times, hackathon account, Singapore):** `flow-data` (CloudFormation, about 40 s) and
  `flow-recorder` (`cdk deploy`, 104 s). `make backfill-hkia` stored all 182 files, 2026-08-15 to 2026-11-13, with no
  failures and no empty days (about 5 min). M0 and M1 pass.
- **AWS surprises:** the permission set allows everything except a deny list: inline role policies, deleting or
  editing roles and policies, CloudTrail, and all billing including Budgets. `cdk bootstrap` would have failed and left a
  stack we could not clean up. Reading the policy first (`aws iam get-role-policy` on our own role) took one minute.
  `cdk deploy` uploads even a small template to the staging bucket, so the stack that creates that bucket is deployed
  with plain CloudFormation. Now AGENTS.md §8.1.4 and §17.3.10.
- **First look at the 91 days (parser on all 182 files):** 77,919 flights; 397 cancelled; 8 status strings the parser
  does not recognise (to inspect in M4). Share of Cathay arrivals more than 30 min late per day: median 8%, worst day 26%
  (2026-08-15). Candidate disruption days: 2026-10-23 (29 Cathay cancellations), 2026-08-15, 2026-10-22, 2026-08-22.
  These are a first scan, not evidence: M4 computes the real numbers.

## M2: API check

- **`make check-apis` (19:05 HKT):** AWS, HKIA, OAG and Google Routes all PASS; results in `docs/api_check.md`. OAG live
  calls used: 4 (one of them a rejected request). M2 passes.
- **OAG surprises:**
  - `CodeType` is required whenever a carrier or airport is given: the first call came back HTTP 400 with that message.
    AGENTS.md §7.3 had it as a default. The client now always sends `CodeType=IATA`.
  - One day of CX arrivals at HKG is 329 records, 33 pages of 10. Query specific flights, never whole days.
  - `statusDetails[]` is not sorted by `updatedAt` (confirmed); the sampled flight had 13 updates.
  - History: 2026-10-14 still returns status updates (8 of the first 10 records).
- **Google Routes:** Central → HKIA T1 two hours ahead: 38 min PESSIMISTIC, 30 min BEST_GUESS, 30 min static.

## M3: Deployed skeleton

- **Deployed 19:25–19:32 HKT** (`make deploy`, 426 s in total, most of it CloudFront). The public URL answers
  `/api/health` over HTTPS with the account ID masked, HTTP redirects to HTTPS, and `/ws-test` loads.
- **Roles:** the app's two roles were added to `flow-data` at 19:23 (the account cannot delete roles, and `flow-app`
  is destroyed often). The task role carries a few spare, project-scoped permissions because it cannot be edited later.
- **What the agent got wrong:**
  - `infra/app.py` shadowed the backend package `app` once pytest had `infra/` on its path: renamed to `cdk_app.py`.
    *Proposed rule (§17.2):* no two top-level Python modules with the same name anywhere in the workspace.
  - Clock times written into this log from memory were wrong by up to an hour and a half. They are now taken from
    CloudFormation and file timestamps. *Proposed rule (§14):* log times from `date` or a service timestamp, never
    from memory.
- **WebSocket hold (19:46–19:57 HKT, laptop → CloudFront → ALB):** 662 s, 133 clock messages, 31 pings,
  longest gap 5.1 s, 0 drops. M3 passes; the same check on a phone (`/ws-test`) is still to do.
- **Image:** 421 MB, linux/arm64, exact versions from `backend/requirements.lock`; built and smoke-tested locally
  before the deploy.

## Engine, scenario and closed loop (backend side of M5–M7), 19:30–19:52 HKT

- **Engine:** `flowcore/engine/` — zone map (`data/reference/hkg_zones.yaml`, ASSUMED distances over REAL stand and
  gate ids), time to gate (Monte Carlo, 2,000 samples), drivers, zones with hysteresis, R0/R1 baselines, and
  `asof.py`, the single place where a flight's published estimates are revealed by replay time.
- **Scenario:** `data/scenarios/2026-10-22-evening/`, 1,042 synthetic passengers on real flights; hero Mei Chen,
  CX254 → CX135, 56% at T−90 (README there). 52 OAG calls for the status histories; ledger at 58 of 800.
- **Replay and policy:** `backend/app/replay/sim.py` — holds, drafts, approve (single and batch), reject, choose,
  automatic conversion only after a missed gate close, expedite with capacity. 12 ms per one-minute tick for 879
  parties on a laptop; a whole 4.5-hour replay in about 2 s.
- **Golden tests pass:** `test_backend_demo_path.py` (the demo story over HTTP and WebSocket) and
  `test_backend_nonnegotiables.py` (one test per non-negotiable, including a leakage test that rewrites the future
  and checks the present does not move). `make test`: 139 passed.
- **What the agent got wrong:**
  - The rationale rounded the chance of missing separately from the draft's field (93% in the text, 0.925 in the
    field). Fixed by rounding once and using that value for both. The non-negotiable test caught it.
  - The WebSocket test client failed TLS on every connect (python.org Python has no CA bundle, §17.2.5) and reported
    437 "drops" that were never the server's. Rerun with `certifi`.
- **Story gap found:** CX254's delay was published at 05:37 HKT (late pushback in London), so Mei is already at
  risk when the replay starts at 16:00; there is no on-screen "slip". Decision pending (start the replay earlier, or
  tell the story as "already at risk").

## Defensible passenger numbers, 20:15–21:30 HKT

- **Why:** the per-pair random count gave every arrival 18–54 connecting passengers, unrelated to aircraft size.
  Now seats × 87.2% load factor × 28% transfer share: 49 (A321neo) to 97 (777-300) per arrival, 1,950 in total.
  Free seats use the same load factor. Every arrival is checked against the formula in
  `research/tests/test_research_scenario.py`.
- **OAG:** a schedule query (10 departures per page) gave aircraft types for 207 of 221 flights. Ledger 127 of 800.
- **What went wrong:**
  - OAG limits calls per minute (HTTP 429, "Try again in N seconds"), and one request timed out. The client now
    waits and retries both. *Proposed rule (§17.4):* every API client honours rate-limit replies and retries
    timeouts.
  - Seat depletion per hour, harmless on a 4.5-hour replay, would have emptied Business on a 15-hour one. Dropped.
- **Test time:** `make test` went from 41 s to 3.5 min (twice the passengers, seeks from 05:30). Acceptable for now.

## M5: Screens, finished 21:23 HKT (start not timed)

- **Built:** `web/` (React 18, Vite 5, TypeScript, Tailwind 3; versions pinned and over two weeks old). Phone (`/app`):
  home, Connect (Plan A / Plan B, keep both or switch, confirm sheet), Plan B confirmed, lock-screen alert, journey
  strip, with live updates over the WebSocket. Staff (`/staff`): inbound-delay card, risk table with approve,
  keep-on-original and Approve all, replay controls, source badges on every number. `/impact` waits for M4.
- **Checked against `docs/design/` at 390×844 and 1440×900** with screenshots driven by Playwright and the local
  Chrome (headless Chrome alone cannot go below about 500 px wide). The whole loop ran: Safe at 05:30 → tight before
  landing → Approve all → lock-screen alert on the phone → switch → Plan B confirmed → staff row "Rebooked on CX105".
- **Copy guard:** `web/src/copy.test.ts` parses every component with the TypeScript compiler and fails on a digit in
  JSX text or a string prop. A first regex version flagged code like `count > 0)`. *Proposed rule (§17.1):* check UI
  copy with a parser, not a regex.
- **What went wrong:** the phone fetched data only after its WebSocket opened and sat on "Loading" in a slow first
  connect; it now also fetches on mount. The London departure showed Hong Kong's date (Thursday) instead of London's
  (Wednesday); times and dates at the origin now use the origin's time zone.
- `make test`: 146 Python tests and 9 web tests pass.

## M4: Backtest and evidence, finished 21:36 HKT

- **Backtest** (`research/flowresearch/backtest.py`): 69,124 tight Cathay connection pairs over 91 days, scored on
  45,826 after a 30-day training window. 15 s on a laptop.
- **What it found first:** the day-before forecast was overconfident (said 47% where 29% broke), and the engine's
  in-flight estimate spread (6 min, ASSUMED) was half of what OAG's estimates actually missed by (11 min, measured on
  30 arrivals, 4 min early on average). Both fixed: late departures from history, and the measured spread and bias.
  Mei's T−90 chance moved from 56% to 42%, still inside AGENTS.md's 30–60%.
- **Result:**
  - **Fixed 38-minute rule:** catches 0% of breaks.
  - **Engine 90 minutes out:** AUC 0.97, catching 93% of breaks while flagging 22% of tight connections.
  - **A day ahead:** AUC 0.68, calibrated but weak.
- **Evidence** (`scripts/build_evidence.py` → `data/evidence.json`, shown on `/impact`): on the scenario evening,
  145 passengers miss; Flow gives 94 an approved plan before landing with 0 wrong bumps; an AURA-style auto-rebook
  would give 75 a plan and wrongly move 23.
- **What went wrong:** build-log times written from memory were wrong twice in this session. *Proposed rule
  (§14):* take every logged time from `date` or a service timestamp.
- *Proposed rule (§17.6):* label a figure that mixes real timing with an assumed model SIMULATED, never REAL.

## Phone screens to the Figma detail, finished 22:13 HKT

- **Alex's review:** the look was not close enough to the Figma, and "Plan A / Plan B" plus the likelihood read oddly.
  Both changed.
- **Phone:** rebuilt against every export at 390×844, screen by screen.
  - **Shared parts:** a status bar (in the laptop frame only), the mint header shape, journey-strip progress with the
    plane, and a ring on the current stop.
  - **Home:** the brushwing mark, Asia Miles, duration and HKG node, and the entry-requirements and alerts cards.
  - **Lock screen:** full date, a stacked notification, the bag notification, torch and camera.
  - **New screens:** Prepare, Navigate, Bags, Arrival and Set up.
- **Staff:** compact rows (the reason shows on hover), a Review button that filters to pending drafts, "✓ Approved".
- **Demo:** `make demo` serves everything locally; nothing is fetched from the internet, so `OFFLINE=1 make demo` works
  with Wi-Fi off. `docs/demo-script.md` is filled in with the real numbers and button presses.
- **Browser test:** `make e2e` (Playwright on the installed Chrome) runs the whole demo loop, including the
  real-time 05:37 slip; passes in 17 s.
- **What went wrong:**
  - Vitest picked up the Playwright file; it now only collects `src/**/*.test.ts`.
  - A "1 of 1" label had been routed through a string trick past the no-digits guard; removed instead. *Proposed
    rule (§17.1):* never work around the copy guard; drop or source the number.

## M8: Gate Planner, finished 22:47 HKT

- **Engine** (`flowcore/engine/gate_planner.py`): road + check-in/bag drop + immigration and security + walk to the
  gate. The deadline is bag drop at departure − 60 with bags, else gate close. "Leave by" is set at the chosen
  percentile. Parameters and sources are in `config/engine.yaml` (`planner`).
- **Re-plans in the replay on real events:** a departure delay once it is published, and the gate once it is
  published. Departure gates and their publish times are now kept from OAG's status history. For example, CX135's
  gate 49 is published at 15:15 and "leave by" moves from 16:35 to 16:40.
- **Road:** Google Routes (PESSIMISTIC as the 95th percentile, BEST_GUESS typical), cached for 5 starting points
  × 11 hours; 112 Google calls in total. It works offline from the cache, and falls back to the Airport Express
  timetable on any failure.
- **Screen:** Travel tools tab.
- **Tests:** engine tests on hand-worked cases; API tests; `make test` 156 Python + 14 web; `make e2e` passes.
- **What went wrong:**
  - The screen's three-second throttle dropped a re-plan that arrived inside the window (a seek while paused), so
    it never caught up. It now plans once the window ends.
  - Two tests expected exact values that depended on sampling or on two changes landing at once; corrected.

### Research notebooks (2026-11-15, about 1 h)
- **Built:** two notebooks for the presentation, saved with outputs (`research/notebooks/`, `make notebooks`):
  the Gate Planner's road and terminal data, and the flight data with the engine's accuracy.
- **Backtest:** split into `build_records` (one row per connection) and `run` (the summary), so the notebooks
  chart the same records. `data/backtest.json` is byte-identical after the change.
- **New result:** with in-flight estimates twice as wrong as measured (±22 min), the engine still catches 90% of
  breaks but flags 33% of tight connections instead of 22%.
- **Found while charting:** the planner's road model lets a drive be faster than Google's no-traffic time (the
  floor is 60% of typical). It does not move the leave-by time, which uses the slow end, but it is visible in
  the chart. Proposed fix: carry Google's `staticDuration` into `Road` and use it as the floor.
- **What went wrong:** pandas stores a missing stand or gate as NaN, not None, which broke the zone lookup once.
