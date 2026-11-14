# Scenario 2026-10-22-evening

Thursday 22 October 2026, the evening arrival wave at Hong Kong. Built by
`uv run python -m flowresearch.build_scenario` from the stored HKIA days and OAG data.

## What is in it

- **Flights (REAL):** 30 Cathay-operated arrivals scheduled 16:45–19:30 and 191 Cathay departures from 17:35 up to
  20 hours later (HKIA past flights: times, stands, gates). Aircraft type is known for 207 of the 221 flights (OAG).
  54 flights carry their OAG status history: estimates as they were published, each with the time it became known.
- **Passengers (SYNTHETIC):** 1,361 parties, 1,950 passengers, connecting off the 30 arrivals; 263 of them on a
  50–89 minute connection. Seed 20261022.
- **History statistics (REAL, derived):** Cathay arrival delays and arrival-wave sizes, 2026-08-15 to 2026-10-21,
  strictly before the scenario day.
- **Replay window:** 05:30–20:30 HKT. It opens before CX254 leaves London, so Mei's slip happens on screen.

## How each number is built (what to say on stage)

| Number | How | Label |
|---|---|---|
| Flights, times, stands, gates | HKIA's published record of the day | REAL |
| How estimates moved in the air | OAG status updates, revealed only once replay time reaches them | REAL |
| Aircraft type per flight | OAG | REAL |
| Seats per cabin | Cathay's published layout for that type (`data/reference/aircraft_seats.yaml`) | ASSUMED |
| Connecting passengers per arrival | seats × **87.2%** load factor × **28%** transfer share | derived from REAL |
| Their cabin | follows that aircraft's real cabin split | SYNTHETIC |
| Their onward flight | a later Cathay departure 50–240 min after, plausible route, tighter gaps less common | SYNTHETIC |
| Names, tiers, groups, preferences | generated from a seed | SYNTHETIC |
| Free seats on later flights | seats per cabin × (1 − 87.2%) | derived from REAL |
| Transfer time (deplane, bus, security, walk) | documented assumptions in `config/engine.yaml` | ASSUMED |
| Accuracy of an in-flight estimate | measured on this evening's 30 arrivals: ±11 min, 4 min early on average | REAL |
| Chance of a late outbound | Cathay departure delays before the scenario day | REAL |
| Chance of missing, holds, drafts | the engine and policy, replayed | SIMULATED |

**Sources:**
- **Load factor:** Cathay Pacific passenger load factor 87.2%, August 2026, the latest monthly release before the
  scenario day (Cathay Group traffic figures).
- **Transfer share:** 1.50 million transfer and transit passengers of 5.37 million at HKIA in October 2025 (AAHK
  monthly figures). The 28% is our division. It is airport-wide, across all airlines. We use it as the share of a
  Cathay flight connecting onward to Cathay within four hours. As the hub airline, Cathay's true transfer share is
  probably higher, but some of those passengers connect later or to partners. The two effects pull in opposite
  directions, so we keep the published figure rather than invent an adjustment.

**Result per arrival:** about 49 connecting passengers on an A321neo (202 seats), 64 on an A330-300 (262), 68 on an
A350-900 (280), 72 on a 777-300ER (294), 82 on an A350-1000 (334) and 97 on a 777-300 (398). The full table is in
`scenario.json` (`connections_per_arrival`), and `research/tests/test_research_scenario.py` checks every arrival
against the formula.

**Free seats:** a load factor is how full flights are on average at departure, so seats × (1 − load factor) is the
number left unsold. For example, an A350-900 has 4 free Business seats (38 × 12.8%) and 27 free Economy (214 × 12.8%).
Our passengers compete for these; families get seats together or not at all, and declared assistance needs go first.

**Known limits:**
- **Departure loads:** only the connecting passengers of the 30 arrivals are modelled, so late departures show few
  connectors.
- **Seat layouts:** the A330-300 (we use the smallest of five layouts) and the 777-300 seat counts are the least
  certain.
- **Spare seats:** the same average spare capacity is applied to every flight; a sold-out flight on the day would
  have less.

## The hero: Mei Chen (SYNTHETIC)

Business class, seat 15A, Gold, prefers the earliest arrival.

| | Flight | Scheduled | Actual | Where |
|---|---|---|---|---|
| Inbound (REAL) | CX254 London → Hong Kong, Boeing 777-300ER | 18:00 | at gate 18:22 | stand N64 |
| Outbound (REAL) | CX135 Hong Kong → Melbourne, Airbus A350-900 | 19:00 | departed 19:00 | gate 49 |

A 60-minute scheduled connection. Gate close 18:45.

**Why this pair (AGENTS.md §3):**
- **The connection:** a real CX → CX pair, 60 minutes scheduled (inside 50–89).
- **The chance:** the engine gives **42%** of missing at 16:51, 90 minutes before the estimated gate arrival (inside
  30–60%).
- **A way out:** later Cathay flights to Melbourne leave the same night and next morning: **CX105** at 00:20 (arrives
  12:15) and **CX163** at 11:20.
- **The stakes:** if she does nothing, she misses CX135 and her held seat is confirmed after gate close.

**How the delay unfolds on screen (OAG, as published):**

| Time (HKT) | Event | Engine shows |
|---|---|---|
| 05:36 | Scheduled 18:00 | Safe, 11% |
| 05:37 | CX254 pushes back in London 13 minutes late; gate estimate 18:23 | |
| 05:40 | | At risk, 47%; a Business seat on CX105 already held; her CX135 seat still hers |
| 06:20 onwards | Gate estimate 18:21 | 42% |
| 18:22 | CX254 reaches the gate | |

Picked on 2026-11-14 from a shortlist scored by the engine over the stored days (`docs/build_log.md`).
