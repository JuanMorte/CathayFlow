# Cathay Flow

Connection Protect for Cathay transfer passengers at Hong Kong: Flow watches a tight connection from the moment the
inbound flight is in the air, holds a backup seat before it is needed, lets staff approve rebookings in one click, and
lets the passenger choose before they land. Built for the Cathay Hackathon 2026.

- **Passenger app** (`/app`):
  - **Home:** the Cathay app home with the Flow entry.
  - **Journey strip:** Home → origin → HKG → destination → Exit.
  - **Prepare:** the leave-home timeline.
  - **In flight:** the original flight (still held) and the flight if it is missed.
  - **At Hong Kong:** the route to the gate.
  - **Also:** the new flight, bags, arrival, set-up and a lock-screen alert.
  - **Travel tools → Gate Planner:** when to leave for the airport when departing Hong Kong.
- **Staff console** (`/staff`, "Flow Ops"): at-risk passengers per inbound flight, recommended backups, approve all.
- **Impact panel** (`/impact`): how often tight connections break on real Hong Kong days, and what Flow changes.

For contributors and coding agents: **`AGENTS.md`** is the source of truth; `CLAUDE.md` adds Claude Code specifics.
Design: `docs/design/`.

## Data and labels

Every number in the API carries a label:

| Label | Meaning | Examples |
|---|---|---|
| **REAL** | Public data | HKIA past flights (times, stands, gates), OAG flight status, Hong Kong Observatory weather, Google Routes |
| **ASSUMED** | Our parameter, documented in `config/` | Deplaning time, walking speed, free seats on later flights |
| **SYNTHETIC** | Generated, seeded | Passengers, bookings, preferences (no real passenger data is used) |
| **SIMULATED** | Output of our replay simulation | Chance of missing, plans before landing, wrong bumps avoided |

### Demo sample data in the passenger app

The passenger app follows Cathay's app design, so it shows no source badges. Some of what that design shows has **no
data source in this demo**, so it is **made up** (generated deterministically per passenger in one file,
`web/src/app/flow/sample.ts`): Asia Miles and Status Points; terminals, lounge, walking pace, seat numbers when the API
has none; the departure time at the origin airport and the arrival time at the destination, and the leave-home
timeline; bags (count, tags, weights, scans, belt); arrival details (immigration wait, exit-by, taxi and transit times,
hotel area). The passengers themselves are synthetic. How many connect off each arrival is built from published figures
(seats × Cathay's load factor × HKIA's transfer share; `data/scenarios/2026-10-22-evening/README.md`). Everything
else is real or simulated and comes from the API. The staff console and impact panel keep their
source badges, and every API payload keeps its labels.

## Run it

- **Local:** `make setup`, then `make demo` → http://localhost:8000 (with Wi-Fi off: `OFFLINE=1 make demo`).
- **Tests:** `make test` runs the unit and golden tests; `make e2e` runs the browser test of the demo loop.
- **Evidence:** `research/README.md` lists the commands that rebuild the scenario, backtest and evidence.

Sources: [HKIA flight information](https://www.hongkongairport.com/) · [OAG Developer Portal](https://developers.oag.com/) ·
[Hong Kong Observatory](https://www.hko.gov.hk/) · [Google Routes API](https://developers.google.com/maps/documentation/routes).
Raw OAG responses are kept in S3, not in this repo.
