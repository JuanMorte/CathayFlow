"""Builds data/evidence.json for the impact panel (AGENTS.md §7.6) from the backtest and a policy replay.

    uv run python -m flowresearch.backtest          # writes data/backtest.json
    uv run python scripts/build_evidence.py         # writes data/evidence.json

It lives in scripts/, not research/, because the policy replay runs the backend's simulation and
research/ never imports backend/ (AGENTS.md §6).

Policy replay on the scenario day (SIMULATED), three ways of handling the same passengers:
- TODAY: no plan before landing; rebooking starts at the transfer desk after the miss (ASSUMED baseline).
- FLOW: backup held when at risk; an agent rebooks every draft (here every 10 minutes) and the original seat stays
  held until its gate closes, so a passenger who makes it after all keeps the original flight.
- AURA-style auto-rebook: anyone at 70% or more one hour before their inbound reaches the gate is moved to a
  later flight automatically, without asking.
A wrong bump is a passenger moved off a flight that, in the replay's ground truth, they would have made.
"""

from __future__ import annotations

import json
import sys
from datetime import timedelta

from app.replay.sim import Sim
from flowcore.config import get_settings

SCENARIO = "2026-10-22-evening"
APPROVE_EVERY = timedelta(minutes=10)
AUTO_REBOOK_AT = timedelta(minutes=60)
AUTO_REBOOK_FROM = 0.70


def policy_replay() -> dict:
    sim = Sim(SCENARIO)
    approved_at: dict[str, object] = {}
    chance_before: dict[str, float] = {}
    t = sim.start
    while t < sim.end:
        t = min(t + APPROVE_EVERY, sim.end)
        sim.advance_to(t)
        for draft in sim.draft_list("PENDING"):
            sim.decide(draft["draft_id"], "approve")
            approved_at[draft["connection_id"]] = sim.t
        for party_id, ps in sim.parties.items():
            landing = ps.inbound.get("actual")
            if party_id not in chance_before and landing and sim.t >= landing - AUTO_REBOOK_AT:
                chance_before[party_id] = ps.assessment.p_miss
    settled = [ps for ps in sim.parties.values() if ps.outcome]
    missed = [ps for ps in settled if ps.outcome == "MISSED"]
    made = [ps for ps in settled if ps.outcome == "MADE"]
    planned = [ps for ps in missed
               if ps.party["party_id"] in approved_at and approved_at[ps.party["party_id"]] <= ps.inbound["actual"]]
    auto = lambda ps: chance_before.get(ps.party["party_id"], 0.0) >= AUTO_REBOOK_FROM  # noqa: E731
    pax = lambda group: sum(ps.size for ps in group)  # noqa: E731
    return {
        "settled_passengers": pax(settled),
        "missed_passengers": pax(missed),
        "flow_plan_before_landing": pax(planned),
        # Counted, not assumed: rebooked by an agent, would have made it, and lost the original seat.
        "flow_wrong_bumps": pax([ps for ps in made if ps.decision == "REBOOK" and not ps.original_seat_held]),
        "flow_rebooked_but_made_it": pax([ps for ps in made if ps.decision == "REBOOK"]),
        "auto_plan_before_landing": pax([ps for ps in missed if auto(ps)]),
        "auto_wrong_bumps": pax([ps for ps in made if auto(ps)]),
        "needs_manual_rebooking": pax([ps for ps in missed if ps.state != "REBOOKED"]),
        "peak_holds": sim.peak_holds,
    }


def item(id_: str, value, unit: str, label: str, source: str, note: str) -> dict:
    return {"id": id_, "value": value, "unit": unit, "label": label, "source": source, "note": note}


def main() -> int:
    root = get_settings().repo_root
    backtest = json.loads((root / "data" / "backtest.json").read_text(encoding="utf-8"))
    policy = policy_replay()
    test = backtest["test"]
    in_flight = test["in_flight_t90"]
    days = f"{backtest['window'][0]} to {backtest['window'][1]}"
    hkia = f"HKIA past flights, {days}; transfer time ASSUMED (config/engine.yaml)"
    replay = f"Replay of {SCENARIO}: real flights, synthetic passengers"
    evidence = [
        # Real timing plus an assumed transfer time: SIMULATED, not REAL.
        item("break_rate_normal", round(backtest["break_rate_normal"] * 100, 1), "%", "SIMULATED", hkia,
             f"of tight Cathay connections (50 to 89 min) break on a normal day ({backtest['pairs_normal']} pairs)"),
        item("break_rate_disrupted", round(backtest["break_rate_disrupted"] * 100, 1), "%", "SIMULATED", hkia,
             f"break on a disrupted day ({len(backtest['disrupted_days'])} days: top tenth for late arrivals, "
             "or 10+ cancellations)"),
        item("next_flight_hours", backtest["next_flight_hours_median"], "h", "REAL", hkia,
             "median wait for the next Cathay flight to the same city after a miss"),
        item("next_flight_6h", round(backtest["next_flight_6h_or_more"] * 100), "%", "REAL", hkia,
             "of misses leave the passenger 6 hours or more until the next flight"),
        item("fixed_rule_caught", round(test["r0_rule"]["breaks_caught"] * 100), "%", "SIMULATED", hkia,
             "of breaks the fixed 38-minute rule flags (it never flags a 50 to 89 minute connection)"),
        item("flow_caught_t90", round(in_flight["at_watch"]["breaks_caught"] * 100), "%", "SIMULATED", hkia,
             f"of breaks Flow flags 90 min before landing, flagging {round(in_flight['at_watch']['flagged_share'] * 100)}% "
             f"of tight connections (in-flight estimates as accurate as OAG's measured ones; {test['pairs']} test pairs)"),
        item("flow_auc_t90", in_flight["auc"], "", "SIMULATED", hkia,
             "how well Flow ranks breaks above connections that hold, 90 min out (0.5 is a coin flip, 1 is perfect)"),
        item("day_before_auc", test["day_before"]["auc"], "", "SIMULATED", hkia,
             "the same score a day ahead, from the schedule alone: little can be known before take-off"),
        item("missed_passengers", policy["missed_passengers"], "passengers", "SIMULATED", replay,
             f"miss their connection on the scenario evening (of {policy['settled_passengers']} whose flight left)"),
        item("today_plan_before_landing", 0, "passengers", "ASSUMED", replay,
             "have a plan before landing today: rebooking starts at the transfer desk after the miss"),
        item("flow_plan_before_landing", policy["flow_plan_before_landing"], "passengers", "SIMULATED", replay,
             "are rebooked by a Cathay agent before landing with Flow"),
        item("auto_plan_before_landing", policy["auto_plan_before_landing"], "passengers", "SIMULATED", replay,
             "would be auto-rebooked before landing by an AURA-style rule (70%+ an hour out)"),
        item("auto_wrong_bumps", policy["auto_wrong_bumps"], "passengers", "SIMULATED", replay,
             "would be moved off a flight they would have made by that auto-rebook rule"),
        item("flow_wrong_bumps", policy["flow_wrong_bumps"], "passengers", "SIMULATED", replay,
             "wrong bumps with Flow: the original seat is kept until its gate closes, so "
             f"{policy['flow_rebooked_but_made_it']} rebooked passengers who made it after all kept their flight"),
        item("oag_estimate_error", backtest["oag_estimate_error"]["sd"], "min", "REAL",
             "OAG Flight Info, 30 Cathay arrivals on 22 Oct 2026",
             "typical error of the in-flight gate estimate 90 min out; the engine uses this spread"),
    ]
    out = root / "data" / "evidence.json"
    out.write_text(json.dumps(evidence, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(policy, indent=1))
    print(f"Wrote {out.relative_to(root)}: {len(evidence)} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
