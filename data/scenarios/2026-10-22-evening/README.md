# Scenario 2026-10-22-evening

Thursday 22 October 2026, the evening arrival wave at Hong Kong. Built by
`uv run python -m flowresearch.build_scenario` from the stored HKIA days and OAG status histories.

## What is in it

- **Flights (REAL):** 30 Cathay-operated arrivals scheduled 16:45–19:30 and 191 Cathay departures from 17:35 up to
  20 hours later (HKIA past flights: times, stands, gates). 54 of them carry their OAG status history (estimates as
  they were published, each with the time it became known).
- **Passengers (SYNTHETIC):** 879 parties, 1,042 passengers, on plausible inbound → outbound pairs with a 50–240
  minute scheduled gap; 138 on a 50–89 minute connection. Seed 20261022.
- **History statistics (REAL, derived):** Cathay arrival delays and arrival-wave sizes from 2026-08-15 to
  2026-10-21, strictly before the scenario day.
- **Replay window:** 16:00–20:30 HKT.

## The hero: Mei Chen (SYNTHETIC)

Business class, seat 15A, Gold, prefers the earliest arrival.

| | Flight | Scheduled | Actual | Where |
|---|---|---|---|---|
| Inbound (REAL) | CX254 London → Hong Kong | 18:00 | at gate 18:22 | stand N64 |
| Outbound (REAL) | CX135 Hong Kong → Melbourne | 19:00 | departed 19:00 | gate 49 |

A 60-minute scheduled connection. Gate close 18:45.

**Why this pair (AGENTS.md §3):** a real CX → CX pair, 60 minutes scheduled (inside 50–89). The engine's chance of
missing 90 minutes before the estimated gate arrival (16:51) is **56%** (inside 30–60%). Later Cathay flights to
Melbourne exist the same night and next morning: **CX105** 00:20 (arrives 12:15) and **CX163** 11:20. If she does
nothing, she misses CX135 and her held seat is confirmed after gate close.

**How the delay unfolds (OAG, as published):** CX254 pushed back in London 13 minutes late; at 05:37 HKT the
in-gate estimate moved from 18:00 to 18:23, and from 06:20 HKT it read 18:21. It reached the gate at 18:22.

Picked on 2026-11-14 from a shortlist scored by the engine over the stored days (docs/build_log.md).
