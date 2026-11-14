"""Time to gate: the one engine behind Connection Protect (AGENTS.md §11.1).

    ready_at_gate = inbound_at_gate + deplane + (bus if remote stand) + transfer_security + walk
    gate_close    = outbound_departure - 15 min
    p_miss        = mean(ready_at_gate > gate_close)

The transfer part (deplane, bus, security, walk) does not depend on the replay time, so it is
drawn once per connection and reused on every tick (§17.5.1). What changes with time is the
inbound gate-time estimate and the outbound departure estimate; `assess` takes those as of t and
must never be given anything that was not known at t (non-negotiable 7).
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

from flowcore.config import find_repo_root
from flowcore.engine.zones import Zones

Zone = str  # "SAFE" | "AT_RISK" | "WONT_MAKE"


@lru_cache(maxsize=4)
def load_config(path: str | None = None) -> dict:
    file = Path(path) if path else find_repo_root() / "config" / "engine.yaml"
    return yaml.safe_load(file.read_text(encoding="utf-8"))


def rng_for(seed: int, *names: str) -> np.random.Generator:
    """A reproducible generator per connection or purpose, independent of call order."""
    return np.random.default_rng([seed, *(zlib.crc32(name.encode()) for name in names)])


def _normal(rng: np.random.Generator, spec: dict, n: int) -> np.ndarray:
    return np.maximum(rng.normal(spec["mean"], spec["sd"], n), spec.get("floor", 0.0))


@dataclass(frozen=True)
class TransferInputs:
    stand: str | None        # inbound stand (REAL when known)
    gate: str | None         # outbound gate (REAL when known)
    cabin: str               # F | J | W | Y
    row_frac: float = 0.5    # 0 = front row of the cabin, 1 = back
    wave_load: float = 0.4   # 0..1, how busy the arrival wave is
    expedite: bool = False   # fast-track or escort offered


@dataclass(frozen=True)
class Transfer:
    """Sampled minutes from aircraft door to departure gate, by component."""
    deplane: np.ndarray
    bus: np.ndarray
    security: np.ndarray
    walk: np.ndarray
    expedite: np.ndarray
    remote: bool
    walk_m: float
    from_zone: str
    to_zone: str

    @property
    def total(self) -> np.ndarray:
        return np.maximum(self.deplane + self.bus + self.security + self.walk - self.expedite, 1.0)


def draw_transfer(inputs: TransferInputs, config: dict, zones: Zones,
                  rng: np.random.Generator) -> Transfer:
    n = int(config["samples"])
    start, end = zones.stand(inputs.stand), zones.gate(inputs.gate)

    cabin = config["deplane"].get(inputs.cabin, config["deplane"]["Y"])
    if "front" in cabin:
        row = min(max(inputs.row_frac, 0.0), 1.0)
        mean = cabin["front"] + (cabin["back"] - cabin["front"]) * row
        deplane = np.maximum(rng.normal(mean, cabin["sd"], n), cabin["floor"])
    else:
        deplane = _normal(rng, cabin, n)

    bus = _normal(rng, config["bus"], n) if start.remote else np.zeros(n)

    security_spec = config["security"]
    load = min(max(inputs.wave_load, 0.0), 1.0)
    security = np.maximum(
        rng.normal(security_spec["base"] + security_spec["per_load"] * load, security_spec["sd"], n),
        security_spec["floor"])

    walk_m = zones.walk_m(start.zone, end.zone)
    speed = _normal(rng, config["walk_speed"], n)
    walk = walk_m / speed / 60.0
    train = zones.train_minutes(start.zone, end.zone)
    if train:
        walk = walk + np.maximum(rng.normal(train, config["train_sd"], n), train / 2)

    expedite = (np.maximum(rng.normal(config["expedite"]["mean"], config["expedite"]["sd"], n), 0.0)
                if inputs.expedite else np.zeros(n))
    return Transfer(deplane, bus, security, walk, expedite, start.remote, walk_m, start.zone, end.zone)


@dataclass(frozen=True)
class Assessment:
    p_miss: float
    ready_p10: datetime
    ready_p50: datetime
    ready_p90: datetime
    gate_close: datetime             # published departure - 15 min
    minutes_available: int           # gate close - expected inbound gate time
    minutes_needed: tuple[int, int]  # transfer P10..P90


def assess(inbound_at_gate: datetime, inbound_noise: np.ndarray | float, transfer: Transfer,
           outbound_departure: datetime, outbound_noise: np.ndarray | float,
           config: dict) -> Assessment:
    """Chance of missing, from what is known now.

    `inbound_at_gate` and `outbound_departure` are the best published times as of now.
    `inbound_noise` and `outbound_noise` are minutes of remaining uncertainty around them
    (arrays of `samples` draws, or 0 once a time is final). A late outbound helps.
    """
    total = transfer.total
    inbound = np.asarray(inbound_noise, dtype=float) + np.zeros_like(total)
    outbound = np.asarray(outbound_noise, dtype=float) + np.zeros_like(total)
    gate_close = outbound_departure - timedelta(minutes=config["gate_close_minutes"])

    slack = (gate_close - inbound_at_gate).total_seconds() / 60.0  # minutes, published times
    ready = inbound + total                                        # minutes after inbound_at_gate
    p_miss = float(np.mean(ready > slack + outbound))

    p10, p50, p90 = np.percentile(ready, [10, 50, 90])
    need10, need90 = np.percentile(total, [10, 90])
    available = slack - float(np.median(inbound))
    at = lambda minutes: inbound_at_gate + timedelta(minutes=float(minutes))  # noqa: E731
    return Assessment(
        p_miss=p_miss,
        ready_p10=at(p10), ready_p50=at(p50), ready_p90=at(p90),
        gate_close=gate_close,
        minutes_available=int(round(available)),
        minutes_needed=(int(round(need10)), int(round(need90))),
    )


def drivers(transfer: Transfer, inbound_delay_min: float, inputs: TransferInputs,
            config: dict, limit: int = 3) -> list[dict]:
    """The components adding the most minutes above a typical connection, as plain sentences."""
    typical = config["typical"]
    security_spec = config["security"]
    typical_security = security_spec["base"] + security_spec["per_load"] * typical["wave_load"]
    typical_walk = typical["walk_m"] / config["walk_speed"]["mean"] / 60.0
    cabin = config["deplane"].get(inputs.cabin, config["deplane"]["Y"])
    typical_deplane = (cabin["front"] + (cabin["back"] - cabin["front"]) * typical["row_frac"]
                       if "front" in cabin else cabin["mean"])

    found = []
    if inbound_delay_min >= 1:
        found.append(("inbound_delay", inbound_delay_min,
                      f"Inbound is running {inbound_delay_min:.0f} min late"))
    if transfer.remote:
        minutes = float(np.mean(transfer.bus))
        found.append(("remote_stand", minutes, f"Remote stand: about {minutes:.0f} min by bus"))
    extra_walk = float(np.mean(transfer.walk)) - typical_walk
    if extra_walk >= 1:
        found.append(("far_gate", extra_walk,
                      f"Far gate: about {extra_walk:.0f} min more walking than usual"))
    extra_security = float(np.mean(transfer.security)) - typical_security
    if extra_security >= 1:
        found.append(("wave_load", extra_security,
                      f"Busy arrival wave: about {extra_security:.0f} min longer at transfer security"))
    extra_deplane = float(np.mean(transfer.deplane)) - typical_deplane
    if extra_deplane >= 1:
        found.append(("deplane_row", extra_deplane,
                      f"Seat near the back: about {extra_deplane:.0f} min longer to leave the aircraft"))
    found.sort(key=lambda item: -item[1])
    return [{"key": key, "minutes": round(minutes, 1), "text": text}
            for key, minutes, text in found[:limit]]


def next_zone(previous: Zone | None, p_miss: float, tau_watch: float, tau_act: float,
              hysteresis: float) -> Zone:
    """SAFE / AT_RISK / WONT_MAKE with a band around each threshold so the status does not flicker."""
    if previous is None:
        return "SAFE" if p_miss < tau_watch else "AT_RISK" if p_miss <= tau_act else "WONT_MAKE"
    if previous == "SAFE":
        if p_miss > tau_act + hysteresis:
            return "WONT_MAKE"
        return "AT_RISK" if p_miss >= tau_watch + hysteresis else "SAFE"
    if previous == "AT_RISK":
        if p_miss < tau_watch - hysteresis:
            return "SAFE"
        return "WONT_MAKE" if p_miss > tau_act + hysteresis else "AT_RISK"
    if p_miss < tau_watch - hysteresis:
        return "SAFE"
    return "AT_RISK" if p_miss < tau_act - hysteresis else "WONT_MAKE"
