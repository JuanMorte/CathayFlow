"""What is known about a flight at replay time t (non-negotiable 7: no leakage).

A flight's `timeline` holds the estimates as they were published (OAG status updates, each with
the time it became known). Its `actual` time is the HKIA record. Both are revealed only once the
replay time has reached them. Everything the engine is given about a flight comes through here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

AIRBORNE_STATES = {"OutGate", "InAir"}


@dataclass(frozen=True)
class FlightView:
    """A flight as known at t."""
    time: datetime                  # best published time: at gate (arrivals) or departure
    noise: np.ndarray | float       # minutes of uncertainty left around `time` (arrivals only)
    status: str                     # Scheduled | Airborne | Landed | At gate | Departed | Cancelled
    est: datetime | None            # published estimate, if any is known at t
    actual: datetime | None         # actual time, only once t has reached it
    source: str                     # "schedule" | "estimate" | "actual"


def events_until(flight: dict, t: datetime) -> list[dict]:
    return [event for event in flight.get("timeline") or [] if event["at"] <= t]


def inbound_view(flight: dict, t: datetime, config: dict, z: np.ndarray,
                 delay_samples: np.ndarray) -> FlightView:
    """Gate-arrival time as known at t.

    `z`: standard normal draws; `delay_samples`: draws from the history of arrival delays, used
    while nothing better than the schedule is known. Both are fixed per connection, so only the
    published times move the result from tick to tick.
    """
    sched = flight["sched"]
    if flight.get("cancelled"):
        return FlightView(sched, 0.0, "Cancelled", None, None, "schedule")
    actual = flight.get("actual")
    if actual and t >= actual:
        return FlightView(actual, 0.0, "At gate", actual, actual, "actual")

    events = events_until(flight, t)
    last = events[-1] if events else None
    est = last.get("est") if last else None
    if last and last.get("on_ground"):
        taxi = config["taxi_in"]
        base = est or last["on_ground"] + timedelta(minutes=taxi["mean"])
        view = FlightView(base, z * taxi["sd"], "Landed", base, None, "estimate")
    elif last and last.get("state") in AIRBORNE_STATES and est:
        sd = config["inbound_estimate_sd"]["airborne"]
        bias = config.get("inbound_estimate_bias", 0)
        view = FlightView(est, bias + z * sd, "Airborne", est, None, "estimate")
    else:
        view = FlightView(sched, delay_samples, "Scheduled", est, None, "schedule")

    # A flight that is not at the gate yet cannot arrive in the past.
    if view.time < t:
        late_by = (t - view.time).total_seconds() / 60.0
        noise = np.maximum(np.asarray(view.noise, dtype=float) - late_by, 0.0)
        return FlightView(t, noise, view.status, view.est, None, view.source)
    return view


def outbound_view(flight: dict, t: datetime) -> FlightView:
    """Published departure time as known at t. The gate closes against this time: a delay only
    helps once the airline has published it."""
    sched = flight["sched"]
    if flight.get("cancelled"):
        return FlightView(sched, 0.0, "Cancelled", None, None, "schedule")
    actual = flight.get("actual")
    published, est = sched, None
    for event in events_until(flight, t):
        if event.get("est"):
            est = event["est"]
    if est and est > sched:
        published = est
    if actual and t >= actual:
        return FlightView(max(published, sched), 0.0, "Departed", est, actual, "actual")
    return FlightView(published, 0.0, "Scheduled", est, None, "estimate" if published != sched else "schedule")


def sample_quantiles(quantiles: list[float], rng: np.random.Generator, n: int) -> np.ndarray:
    """Draw from a distribution given as evenly spaced quantiles (inverse-transform sampling)."""
    points = np.asarray(quantiles, dtype=float)
    return np.interp(rng.random(n), np.linspace(0.0, 1.0, len(points)), points)
