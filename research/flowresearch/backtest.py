"""Backtest: the time-to-gate engine on 91 real Hong Kong days (AGENTS.md §9, §7.6).

    uv run python -m flowresearch.backtest          # prints the results, writes data/backtest.json

What is real and what is assumed:
- REAL: every Cathay-operated arrival and departure, 2026-08-15 to 2026-11-13 (HKIA): scheduled and actual times,
  stands, gates, cancellations.
- ASSUMED: the transfer time (deplane, security, walk) from config/engine.yaml, for a typical Economy passenger
  in the middle of the cabin. There are no public passenger outcomes, so "the connection broke" means: the real
  gate-arrival time plus the typical transfer time is later than the real gate close.
- Tight connection: a Cathay → Cathay pair, 50 to 89 minutes scheduled, plausible route
  (data/reference/airports.yaml), neither flight cancelled.

The forecast is made before the inbound leaves its origin, from the schedule and the delay history only (the
in-flight estimates exist only for flights whose OAG history we pulled). History comes from a training window;
results are reported on the later days only, so nothing is learned from the days being scored.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import yaml

from flowcore.config import get_settings
from flowcore.engine.asof import sample_quantiles
from flowcore.engine.time_to_gate import TransferInputs, assess, draw_transfer, load_config, rng_for
from flowcore.engine.zones import load_zones
from flowcore.parse.hkia import delay_minutes, parse_envelopes
from flowresearch import synth

TRAIN_DAYS = 30           # 2026-08-15 .. 2026-09-13: history for the forecasts
SAMPLES = 1000
SEED = 20261114


def load_rows(settings) -> list[dict]:
    files = sorted((settings.data_dir / "raw" / "hkia").glob("past_*.json"))
    if not files:
        raise SystemExit("No HKIA days in data/raw/hkia. Run `make data-down` first.")
    return parse_envelopes(json.loads(file.read_text(encoding="utf-8")) for file in files)


def disruption_days(cathay: list[dict]) -> tuple[set[date], dict]:
    """ASSUMED definition: a day is disrupted if its share of Cathay arrivals more than 30 min late is in the
    top tenth of days, or 10 or more Cathay flights were cancelled."""
    late, cancelled, count = defaultdict(int), defaultdict(int), defaultdict(int)
    for row in cathay:
        if row["cancelled"]:
            cancelled[row["sched_date"]] += 1
        elif row["kind"] == "arr" and row["actual"]:
            count[row["sched_date"]] += 1
            late[row["sched_date"]] += delay_minutes(row) > 30
    share = {day: late[day] / count[day] for day in count if count[day] >= 50}
    cut = float(np.quantile(list(share.values()), 0.9))
    days = {day for day, value in share.items() if value >= cut} | {d for d, n in cancelled.items() if n >= 10}
    return days, {"late_share_cut": round(cut, 3)}


def tight_pairs(cathay: list[dict], airports: dict, implausible: list) -> list[tuple[dict, dict]]:
    arrivals = [r for r in cathay if r["kind"] == "arr" and not r["cancelled"] and r["actual"]]
    departures = sorted((r for r in cathay if r["kind"] == "dep" and not r["cancelled"] and r["actual"]),
                        key=lambda r: r["sched"])
    starts = [d["sched"] for d in departures]
    import bisect
    pairs = []
    for inbound in arrivals:
        low = bisect.bisect_left(starts, inbound["sched"] + timedelta(minutes=50))
        high = bisect.bisect_right(starts, inbound["sched"] + timedelta(minutes=89))
        for outbound in departures[low:high]:
            if synth.plausible(inbound["airport"], outbound["airport"], airports, implausible):
                pairs.append((inbound, outbound))
    return pairs


def auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Chance that a broken connection gets a higher score than one that held (ties count half)."""
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores))
    ranks[order] = np.arange(1, len(scores) + 1)
    for value in np.unique(scores):                       # average ranks over ties
        mask = scores == value
        ranks[mask] = ranks[mask].mean()
    positives = labels.sum()
    negatives = len(labels) - positives
    return float((ranks[labels].sum() - positives * (positives + 1) / 2) / (positives * negatives))


def run() -> dict:
    settings = get_settings()
    root = settings.repo_root
    config = {**load_config(), "samples": SAMPLES}
    zones = load_zones()
    airports_file = yaml.safe_load((root / "data" / "reference" / "airports.yaml").read_text())
    rows = load_rows(settings)
    cathay = [r for r in rows if r["carrier"] == "CX"]
    first_day = min(r["sched_date"] for r in cathay)
    split = first_day + timedelta(days=TRAIN_DAYS)
    disrupted, disruption_rule = disruption_days(cathay)

    train = [r for r in cathay if r["actual"] and not r["cancelled"] and r["sched_date"] < split]
    quantiles = list(np.quantile([delay_minutes(r) for r in train if r["kind"] == "arr"], np.linspace(0, 1, 41)))
    # A late departure moves gate close later; an early one does not move it earlier.
    out_quantiles = list(np.quantile([max(delay_minutes(r), 0.0) for r in train if r["kind"] == "dep"],
                                     np.linspace(0, 1, 41)))
    oag_errors = measured_estimate_errors(root)

    pairs = tight_pairs(cathay, airports_file["airports"], airports_file["implausible_pairs"])
    by_destination = defaultdict(list)
    for row in cathay:
        if row["kind"] == "dep" and not row["cancelled"]:
            by_destination[row["airport"]].append(row["sched"])
    for times in by_destination.values():
        times.sort()

    records = []
    for inbound, outbound in pairs:
        key = f"{inbound['flight']}>{outbound['flight']}@{inbound['sched']:%Y%m%d}"
        rng = rng_for(SEED, key)
        transfer = draw_transfer(TransferInputs(inbound["stand"], outbound["gate"], "Y", 0.5, 0.4), config, zones, rng)
        typical = float(np.median(transfer.total))
        # One passenger's transfer time, drawn from the same model the forecast uses.
        passenger = float(transfer.total[int(rng.integers(SAMPLES))])
        gate_close = max(outbound["sched"], outbound["actual"]) - timedelta(minutes=config["gate_close_minutes"])
        broke = inbound["actual"] + timedelta(minutes=passenger) > gate_close
        out_noise = sample_quantiles(out_quantiles, rng, SAMPLES)
        # Day before: schedule and delay history only.
        forecast = assess(inbound["sched"], sample_quantiles(quantiles, rng, SAMPLES), transfer,
                          outbound["sched"], 0.0, config).p_miss
        day_before = assess(inbound["sched"], sample_quantiles(quantiles, rng, SAMPLES), transfer,
                            outbound["sched"], out_noise, config).p_miss
        # 90 min before landing: an in-flight estimate as wrong as OAG's measured estimates were.
        estimate = inbound["actual"] + timedelta(minutes=float(rng.choice(oag_errors)))
        spread = float(np.std(oag_errors))
        in_flight = assess(estimate, -float(np.mean(oag_errors)) + rng.standard_normal(SAMPLES) * spread,
                           transfer, outbound["sched"], out_noise, config).p_miss
        later = [t for t in by_destination[outbound["airport"]] if t > outbound["sched"]]
        records.append({
            "day": inbound["sched_date"], "disrupted": inbound["sched_date"] in disrupted,
            "gap": (outbound["sched"] - inbound["sched"]).total_seconds() / 60, "broke": broke,
            "p": forecast, "p_day_before": day_before, "p_in_flight": in_flight, "typical_transfer": typical,
            "next_hours": (later[0] - outbound["sched"]).total_seconds() / 3600 if later else None,
        })

    test = [r for r in records if r["day"] >= split]
    labels = np.array([r["broke"] for r in test])
    scores = np.array([r["p"] for r in test])
    day_scores = np.array([r["p_day_before"] for r in test])
    flight_scores = np.array([r["p_in_flight"] for r in test])
    gaps = np.array([r["gap"] for r in test])
    policy = yaml.safe_load((root / "config" / "policy.yaml").read_text())

    def flag_stats(flags: np.ndarray) -> dict:
        caught = int((flags & labels).sum())
        return {"flagged_share": round(float(flags.mean()), 3),
                "breaks_caught": round(caught / max(int(labels.sum()), 1), 3),
                "precision": round(caught / max(int(flags.sum()), 1), 3)}

    normal = [r for r in records if not r["disrupted"]]
    bad = [r for r in records if r["disrupted"]]
    misses = [r for r in records if r["broke"] and r["next_hours"] is not None]
    result = {
        "window": [str(first_day), str(max(r["sched_date"] for r in cathay))],
        "train_until": str(split - timedelta(days=1)),
        "days": len({r["sched_date"] for r in cathay}),
        "disrupted_days": sorted(str(d) for d in disrupted),
        "disruption_rule": disruption_rule,
        "tight_pairs": len(records),
        "break_rate_all": round(float(np.mean([r["broke"] for r in records])), 4),
        "break_rate_normal": round(float(np.mean([r["broke"] for r in normal])), 4),
        "break_rate_disrupted": round(float(np.mean([r["broke"] for r in bad])), 4) if bad else None,
        "pairs_normal": len(normal), "pairs_disrupted": len(bad),
        "next_flight_hours_median": round(float(np.median([r["next_hours"] for r in misses])), 1) if misses else None,
        "next_flight_6h_or_more": round(float(np.mean([r["next_hours"] >= 6 for r in misses])), 3) if misses else None,
        "typical_transfer_median": round(float(np.median([r["typical_transfer"] for r in records])), 1),
        "oag_estimate_error": {"flights": len(oag_errors), "mean": round(float(np.mean(oag_errors)), 1),
                               "sd": round(float(np.std(oag_errors)), 1)},
        "test": {
            "pairs": len(test), "breaks": int(labels.sum()),
            "base_rate": round(float(labels.mean()), 4),
            "old_engine_day_before": summary(scores, labels, policy),
            "day_before": summary(day_scores, labels, policy),
            "in_flight_t90": summary(flight_scores, labels, policy),
            "engine_auc": round(auc(scores, labels), 3),
            "gap_only_auc": round(auc(-gaps, labels), 3),
            "engine_brier": round(float(np.mean((scores - labels) ** 2)), 4),
            "base_rate_brier": round(float(np.mean((labels.mean() - labels) ** 2)), 4),
            "r0_rule": flag_stats(gaps < config["baseline_r0_minutes"]),
            "engine_at_watch": flag_stats(scores >= policy["tau_watch"]),
            "engine_at_offer": flag_stats(scores >= policy["tau_offer"]),
            "calibration": calibration(scores, labels),
        },
    }
    return result


def measured_estimate_errors(root: Path) -> list[float]:
    """Minutes by which OAG's in-gate estimate, 90 min before the real gate time, missed it (REAL, scenario
    flights; negative = the estimate was early)."""
    from flowcore.scenario import load_scenario
    errors = []
    for flight in load_scenario("2026-10-22-evening")["flights"].values():
        if flight["kind"] != "arr" or not flight["timeline"] or not flight["actual"]:
            continue
        t = flight["actual"] - timedelta(minutes=90)
        known = [e for e in flight["timeline"] if e["at"] <= t and e["est"] and e["state"] in ("OutGate", "InAir")]
        if known:
            errors.append((known[-1]["est"] - flight["actual"]).total_seconds() / 60)
    return errors


def summary(scores: np.ndarray, labels: np.ndarray, policy: dict) -> dict:
    caught = lambda flags: round(float((flags & labels).sum() / max(labels.sum(), 1)), 3)  # noqa: E731
    precise = lambda flags: round(float((flags & labels).sum() / max(flags.sum(), 1)), 3)  # noqa: E731
    watch, offer = scores >= policy["tau_watch"], scores >= policy["tau_offer"]
    return {"auc": round(auc(scores, labels), 3), "brier": round(float(np.mean((scores - labels) ** 2)), 4),
            "at_watch": {"flagged_share": round(float(watch.mean()), 3), "breaks_caught": caught(watch),
                         "precision": precise(watch)},
            "at_offer": {"flagged_share": round(float(offer.mean()), 3), "breaks_caught": caught(offer),
                         "precision": precise(offer)},
            "calibration": calibration(scores, labels)}


def calibration(scores: np.ndarray, labels: np.ndarray) -> list[dict]:
    bins = [0.0, 0.1, 0.2, 0.4, 0.7, 1.01]
    rows = []
    for low, high in zip(bins, bins[1:]):
        mask = (scores >= low) & (scores < high)
        if mask.sum():
            rows.append({"from": low, "to": min(high, 1.0), "pairs": int(mask.sum()),
                         "predicted": round(float(scores[mask].mean()), 3),
                         "observed": round(float(labels[mask].mean()), 3)})
    return rows


def main() -> int:
    result = run()
    out = get_settings().repo_root / "data" / "backtest.json"
    out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "disrupted_days"}, indent=1))
    print(f"Disrupted days: {', '.join(result['disrupted_days'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
