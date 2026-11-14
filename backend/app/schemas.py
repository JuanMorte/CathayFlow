"""API contract (AGENTS.md §10). `make contract` exports it to contracts/openapi.json.

Times are ISO-8601 with +08:00. Every object carrying numbers has `labels`, a map from field name
to REAL (public data), ASSUMED (our parameter), SYNTHETIC (generated) or SIMULATED (engine output).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Label = Literal["REAL", "ASSUMED", "SYNTHETIC", "SIMULATED"]
Zone = Literal["SAFE", "AT_RISK", "WONT_MAKE"]
ConnState = Literal["MONITORING", "BACKUP_HELD", "DRAFT_PENDING", "OFFERED",
                    "PASSENGER_CHOSE", "MADE_ORIGINAL", "REBOOKED"]
OptionKind = Literal["ORIGINAL_EXPEDITE", "ALT_FLIGHT", "OVERNIGHT"]


class Health(BaseModel):
    ok: bool
    version: str
    offline: bool
    bucket: str | None  # account ID masked (AGENTS.md §17.3.7)
    scenario: str | None


class ScenarioInfo(BaseModel):
    id: str
    title: str


class ReplayState(BaseModel):
    scenario_id: str
    t: datetime
    speed: float          # simulated seconds per real second
    playing: bool
    start: datetime
    end: datetime
    hero_pid: str


class ReplayLoad(BaseModel):
    scenario_id: str


class ReplayControl(BaseModel):
    action: Literal["play", "pause", "seek", "speed", "reset"]
    t: datetime | None = None
    speed: float | None = None


class FlightRef(BaseModel):
    flight: str
    origin: str
    dest: str
    origin_city: str
    dest_city: str
    sched: datetime
    est: datetime | None      # only if known at t
    actual: datetime | None   # only if known at t
    stand: str | None
    gate: str | None
    status: str               # Scheduled | Airborne | Landed | At gate | Departed | Cancelled
    labels: dict[str, str]


class TimeRange(BaseModel):
    p10: datetime
    p50: datetime
    p90: datetime


class Driver(BaseModel):
    key: str                  # inbound_delay | remote_stand | far_gate | wave_load | deplane_row
    minutes: float
    text: str


class Hold(BaseModel):
    hold_id: str
    flight: str
    dep: datetime
    cabin: str
    seat: str | None
    expires_at: datetime


class ConnectionStatus(BaseModel):
    connection_id: str
    pid: str
    passenger_name: str
    cabin: str
    group_size: int
    assistance: bool
    tier: str
    t: datetime
    inbound: FlightRef
    outbound: FlightRef
    gate_close: datetime
    ready_at_gate: TimeRange
    minutes_available: int              # gate close - expected arrival at the inbound gate
    minutes_needed: tuple[int, int]     # transfer P10..P90
    p_miss: float
    zone: Zone
    state: ConnState
    drivers: list[Driver]
    backup_hold: Hold | None
    expedite_offered: bool
    original_seat_held: bool            # non-negotiable 1
    outcome: Literal["MADE", "MISSED"] | None
    labels: dict[str, str]


class Option(BaseModel):
    option_id: str
    kind: OptionKind
    title: str
    flight: str
    dep: datetime
    final_arrival: datetime | None      # scheduled, local time at the destination; None if no source
    cabin: str
    seat: str | None
    guaranteed: bool                    # False for ORIGINAL_EXPEDITE ("if you make the gate")
    extras: list[str]
    approved: bool
    labels: dict[str, str]


class Draft(BaseModel):
    draft_id: str
    connection_id: str
    pid: str
    passenger_name: str
    cabin: str
    group_size: int
    assistance: bool
    tier: str
    p_miss: float
    zone: Zone
    inbound_flight: str
    outbound_flight: str
    option: Option
    rationale: str
    status: Literal["PENDING", "APPROVED", "REJECTED"]
    note: str | None = None
    labels: dict[str, str]


class Passenger(BaseModel):
    pid: str
    name: str
    cabin: str
    seat: str
    tier: str
    group_size: int
    assistance: bool
    preference: str
    is_synthetic: bool
    labels: dict[str, str]


class Trip(BaseModel):
    passenger: Passenger
    inbound: FlightRef
    outbound: FlightRef
    sched_gap_min: int
    labels: dict[str, str]


class ChooseRequest(BaseModel):
    option_id: str


class DraftDecision(BaseModel):
    decision: Literal["approve", "reject"]
    note: str | None = None


class ApproveBatch(BaseModel):
    ids: list[str]


class InboundSummary(BaseModel):
    flight: str
    origin: str
    origin_city: str
    sched: datetime
    est: datetime | None
    actual: datetime | None
    status: str
    delay_min: int | None               # published or actual delay, if known at t
    stand: str | None
    connecting: int
    at_risk: int
    wont_make: int
    labels: dict[str, str]


class WaveSummary(BaseModel):
    t: datetime
    connecting: int
    safe: int
    at_risk: int
    wont_make: int
    holds: int
    peak_holds: int
    drafts_pending: int
    drafts_approved: int
    rebooked: int
    made_original: int
    inbounds: list[InboundSummary]
    labels: dict[str, str]


class Wave(BaseModel):
    summary: WaveSummary
    connections: list[ConnectionStatus]


class ImpactMetric(BaseModel):
    id: str
    value: float | int | str | None
    unit: str
    label: Label
    source: str
    note: str


class WsMessage(BaseModel):
    """Every WebSocket message: `clock`, `connection_update`, `draft_update`, `options_update`,
    `notification` or `ping`."""

    type: str
    t: datetime | None = None
    payload: dict = {}
