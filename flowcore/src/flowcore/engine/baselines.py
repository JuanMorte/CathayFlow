"""Simple rules kept for comparison with the engine (AGENTS.md §11.1).

R0: a fixed 38-minute rule (deplane 8 + transfer 15 + gate close 15).
R1: R0 with the predicted outbound delay added to the departure time.
"""

from __future__ import annotations

from datetime import datetime


def r0_misses(inbound_at_gate: datetime, outbound_departure: datetime, config: dict) -> bool:
    gap = (outbound_departure - inbound_at_gate).total_seconds() / 60.0
    return gap < config["baseline_r0_minutes"]


def r1_misses(inbound_at_gate: datetime, outbound_departure: datetime,
              predicted_outbound_delay_min: float, config: dict) -> bool:
    gap = (outbound_departure - inbound_at_gate).total_seconds() / 60.0
    return gap + max(predicted_outbound_delay_min, 0.0) < config["baseline_r0_minutes"]
