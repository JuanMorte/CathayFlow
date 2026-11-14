"""The replay simulation: clock time in, engine and policy out (AGENTS.md §4, §11).

`Sim` is plain synchronous Python with no network and no asyncio, so tests can drive it directly.
Each `advance_to(t)` reveals what is known at t (flowcore.engine.asof), recomputes the affected
connections, moves the policy state machine, and returns the events to push to open screens.

    MONITORING -(at risk)-> BACKUP_HELD -(drafted)-> DRAFT_PENDING -(staff approve)-> OFFERED
        ^                       |                         | (reject -> BACKUP_HELD, logged)
        +--(safe for 2 ticks)---+ release hold            v
                                                  PASSENGER_CHOSE -> MADE_ORIGINAL | REBOOKED

Non-negotiables enforced here: the original seat is released only through
`seats.release_original_seat`; nothing is offered as confirmed before staff approve it; nothing is
booked without the passenger's choice, except converting a held seat after a missed gate close.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import yaml

from app.policy import seats as seat_rules
from app.policy.rationale import CABIN_NAMES, rationale
from app.policy.seats import Seats
from flowcore.config import find_repo_root
from flowcore.engine.asof import FlightView, inbound_view, outbound_view, sample_quantiles
from flowcore.engine.time_to_gate import (Assessment, TransferInputs, assess, draw_transfer,
                                          drivers, load_config, next_zone, rng_for)
from flowcore.engine.zones import load_zones
from flowcore.scenario import load_scenario

STEP = timedelta(minutes=1)
SEEK_STEP = timedelta(minutes=5)        # AGENTS.md §17.5.8
LOWER_CABINS = {"F": ["F", "J", "W", "Y"], "J": ["J", "W", "Y"], "W": ["W", "Y"], "Y": ["Y"]}
FINAL_STATES = {"MADE_ORIGINAL", "REBOOKED"}


class PolicyError(RuntimeError):
    """A request the rules do not allow (unknown id, unapproved option, already decided)."""


def load_policy(path: str | None = None) -> dict:
    file = Path(path) if path else find_repo_root() / "config" / "policy.yaml"
    return yaml.safe_load(file.read_text(encoding="utf-8"))


@dataclass
class PartyState:
    party: dict
    inbound: dict
    outbound: dict
    transfer: object
    transfer_fast: object
    z: np.ndarray
    delay: np.ndarray
    true_index: int                      # which sample is this party's "real" transfer time
    out_delay: np.ndarray | float = 0.0  # possible outbound delays (minutes) while none is published
    zone: str | None = None
    state: str = "MONITORING"
    assessment: Assessment | None = None
    in_view: FlightView | None = None
    out_view: FlightView | None = None
    view_key: tuple | None = None
    driver_list: list = field(default_factory=list)
    hold: dict | None = None
    draft_id: str | None = None
    rejected: bool = False
    expedite_offered: bool = False
    chosen_kind: str | None = None
    booked: dict | None = None           # the flight they were moved to, once rebooked
    original_seat_held: bool = True
    release_reason: str | None = None
    safe_ticks: int = 0
    outcome: str | None = None           # MADE | MISSED, from the replay's ground truth
    auto_converted: bool = False

    @property
    def pid(self) -> str:
        return self.party["members"][0]["pid"]

    @property
    def name(self) -> str:
        return self.party["members"][0]["name"]

    @property
    def size(self) -> int:
        return self.party["size"]

    @property
    def final(self) -> bool:
        return self.state in FINAL_STATES or self.outcome is not None

    @property
    def uses_expedite(self) -> bool:
        return self.chosen_kind == "ORIGINAL_EXPEDITE" and self.expedite_offered


class Sim:
    def __init__(self, scenario_id: str, config: dict | None = None, policy: dict | None = None):
        self.scenario = load_scenario(scenario_id)
        self.meta = self.scenario["meta"]
        self.flights = self.scenario["flights"]
        self.config = config or load_config()
        self.policy = policy or load_policy()
        self.zones = load_zones()
        self.seed = int(self.meta["seed"])
        self.start: datetime = self.meta["replay_start"]
        self.end: datetime = self.meta["replay_end"]
        self._departures_by_airport: dict[str, list[dict]] = {}
        for flight in sorted(self.flights.values(), key=lambda f: f["sched"]):
            if flight["kind"] == "dep":
                self._departures_by_airport.setdefault(flight["airport"], []).append(flight)
        self.reset()

    # ------------------------------------------------------------------ set-up

    def reset(self) -> None:
        self.t: datetime = self.start
        self.seats = Seats(self.policy, self.flights, self.meta.get("load_factor"))
        self.drafts: dict[str, dict] = {}
        self.log: list[dict] = []
        self.peak_holds = 0
        self._hold_counter = 0
        self._draft_counter = 0
        self._expedite_used: dict[datetime, int] = {}
        self.parties: dict[str, PartyState] = {}
        self.by_pid: dict[str, PartyState] = {}
        samples = int(self.config["samples"])
        for party in self.scenario["parties"]:
            inbound, outbound = self.flights[party["inbound"]], self.flights[party["outbound"]]
            inputs = TransferInputs(inbound["stand"], outbound["gate"], party["cabin"],
                                    party["row_frac"], inbound.get("wave_load", 0.4))
            # Stands and gates are treated as known for the whole replay (ASSUMED, §17.4.7).
            # Transfer times do not depend on t, so they are drawn once here (§17.5.1).
            transfer = draw_transfer(inputs, self.config, self.zones, rng_for(self.seed, party["party_id"]))
            fast = draw_transfer(TransferInputs(inputs.stand, inputs.gate, inputs.cabin, inputs.row_frac,
                                                inputs.wave_load, expedite=True),
                                 self.config, self.zones, rng_for(self.seed, party["party_id"]))
            rng = rng_for(self.seed, party["party_id"], "inbound")
            state = PartyState(
                party=party, inbound=inbound, outbound=outbound, transfer=transfer, transfer_fast=fast,
                z=rng.standard_normal(samples),
                delay=sample_quantiles(self.meta["inbound_delay_quantiles"], rng, samples),
                true_index=int(rng.integers(samples)),
            )
            # History of departure delays: a late outbound gives more time until it is known.
            state.out_delay = sample_quantiles(self.meta.get("outbound_delay_quantiles") or [0.0, 0.0], rng, samples)
            self.parties[party["party_id"]] = state
            for member in party["members"]:
                self.by_pid[member["pid"]] = state
        self._step(self.t)

    # ------------------------------------------------------------------ clock

    def advance_to(self, target: datetime, step: timedelta = STEP) -> list[dict]:
        """Move forward to `target`, one engine step per simulated minute. Returns events."""
        target = min(target, self.end)
        events: list[dict] = []
        while self.t < target:
            self.t = min(self.t + step, target)
            events += self._step(self.t)
        return events

    def seek(self, target: datetime) -> list[dict]:
        """Jump to a time. Going back resets and replays; staff and passenger decisions are lost."""
        target = max(self.start, min(target, self.end))
        if target < self.t:
            self.reset()
        self.advance_to(target, SEEK_STEP)
        return [{"type": "reload", "to": "all", "payload": {}}]

    # ------------------------------------------------------------------ one tick

    def _transfer_of(self, ps: PartyState):
        return ps.transfer_fast if ps.uses_expedite else ps.transfer

    def _assess(self, ps: PartyState, t: datetime) -> bool:
        """Refresh what is known and the chance of missing. True if anything changed."""
        in_view = inbound_view(ps.inbound, t, self.config, ps.z, ps.delay)
        out_view = outbound_view(ps.outbound, t)
        key = (in_view.time, in_view.status, out_view.time, out_view.status, ps.uses_expedite)
        if key == ps.view_key:
            return False
        transfer = self._transfer_of(ps)
        out_noise = ps.out_delay if out_view.source == "schedule" else 0.0
        assessment = assess(in_view.time, in_view.noise, transfer, out_view.time, out_noise, self.config)
        if "Cancelled" in (in_view.status, out_view.status):
            assessment = Assessment(1.0, assessment.ready_p10, assessment.ready_p50, assessment.ready_p90,
                                    assessment.gate_close, assessment.minutes_available,
                                    assessment.minutes_needed)
        delay = (in_view.time - ps.inbound["sched"]).total_seconds() / 60.0 if in_view.source != "schedule" else 0.0
        inputs = TransferInputs(ps.inbound["stand"], ps.outbound["gate"], ps.party["cabin"],
                                ps.party["row_frac"], ps.inbound.get("wave_load", 0.4))
        ps.driver_list = drivers(transfer, delay, inputs, self.config)
        ps.in_view, ps.out_view, ps.view_key, ps.assessment = in_view, out_view, key, assessment
        return True

    def _step(self, t: datetime) -> list[dict]:
        changed: set[str] = set()
        notes: list[dict] = []
        policy = self.policy
        for party_id, ps in self.parties.items():
            if ps.final:
                continue
            if self._assess(ps, t):
                changed.add(party_id)
            before = (ps.zone, ps.state)
            ps.zone = next_zone(ps.zone, ps.assessment.p_miss, policy["tau_watch"], policy["tau_act"],
                                policy["hysteresis"])
            if self._resolve_at_gate_close(ps, t, notes):
                changed.add(party_id)
                continue
            if ps.zone == "SAFE":
                ps.safe_ticks += 1
                if ps.state == "BACKUP_HELD" and ps.safe_ticks >= policy["safe_ticks_to_release"]:
                    self._release_hold(ps, "safe again")
                    ps.state = "MONITORING"
            else:
                ps.safe_ticks = 0
            if (ps.zone, ps.state) != before:
                changed.add(party_id)

        for ps in self._hold_queue():
            if self._try_hold(ps, t):
                changed.add(ps.party["party_id"])
                landing = ps.in_view.est or ps.in_view.time
                notes.append(self._note(ps, "Tight connection in Hong Kong",
                                        f"{ps.inbound['flight']} now lands {landing:%H:%M}. We've already held "
                                        "a backup seat for you, just in case."))
        self._offer_expedite(t, changed)
        draft_events = []
        for ps in self.parties.values():
            if self._maybe_draft(ps, t):
                changed.add(ps.party["party_id"])
                draft_events.append({"type": "draft_update", "to": "staff",
                                     "payload": self.draft_view(self.drafts[ps.draft_id])})
        self.peak_holds = max(self.peak_holds, self.seats.held_total())
        events = [{"type": "connection_update", "to": "staff+passenger", "pid": self.parties[p].pid,
                   "pids": [m["pid"] for m in self.parties[p].party["members"]],
                   "payload": self.status_view(self.parties[p])} for p in sorted(changed)]
        return events + draft_events + notes

    # ------------------------------------------------------------------ outcome

    def _resolve_at_gate_close(self, ps: PartyState, t: datetime, notes: list[dict]) -> bool:
        """At the original gate close, the replay's ground truth decides who made it."""
        gate_close = ps.assessment.gate_close
        if t < gate_close:
            return False
        arrived = ps.inbound.get("actual")
        cancelled = ps.inbound.get("cancelled") or ps.outbound.get("cancelled")
        made = False
        if not cancelled and arrived and arrived <= t:
            true_transfer = float(self._transfer_of(ps).total[ps.true_index])
            made = arrived + timedelta(minutes=true_transfer) <= gate_close
        if made:
            ps.outcome, ps.state = "MADE", "MADE_ORIGINAL"
            self._release_hold(ps, "made the original flight")
            self._close_draft(ps, "Made the original flight")
            return True
        ps.outcome = "MISSED"
        if ps.hold:
            # The only automatic move, and only after the miss (AGENTS.md §11.2).
            seat_rules.release_original_seat(ps, seat_rules.GATE_CLOSED, t, gate_close)
            ps.booked, ps.hold, ps.state, ps.auto_converted = ps.hold, None, "REBOOKED", True
            self._close_draft(ps, "Held seat confirmed after the missed gate close")
            notes.append(self._note(ps, "You are on the later flight",
                                    f"Your held seat on {ps.booked['flight_no']} is confirmed."))
        self._log(t, "outcome", ps, outcome=ps.outcome, state=ps.state)
        return True

    # ------------------------------------------------------------------ holds

    def _score(self, ps: PartyState) -> float:
        policy = self.policy
        return (ps.assessment.p_miss * policy["tier_weight"].get(ps.party["tier"], 1.0)
                * policy["cabin_weight"].get(ps.party["cabin"], 1.0))

    def _hold_queue(self) -> list[PartyState]:
        """Who gets a backup seat first: assistance needs, then the weighted chance of missing.
        Tier is a weight inside the score, never an override (non-negotiable 4)."""
        waiting = [ps for ps in self.parties.values()
                   if not ps.final and ps.hold is None and ps.zone in ("AT_RISK", "WONT_MAKE")
                   and ps.state in ("MONITORING", "BACKUP_HELD")]
        return sorted(waiting, key=lambda ps: (not ps.party["assistance"], -self._score(ps),
                                               ps.party["party_id"]))

    def alternatives(self, ps: PartyState, t: datetime) -> list[dict]:
        """Later Cathay flights to the same city that this passenger could still catch."""
        window = timedelta(hours=self.policy["alternative_window_hours"])
        earliest = ps.assessment.ready_p90 + timedelta(minutes=self.config["gate_close_minutes"] + 10)
        found = []
        for flight in self._departures_by_airport.get(ps.outbound["airport"], []):
            if flight["key"] == ps.outbound["key"] or flight["sched"] <= ps.outbound["sched"]:
                continue
            if flight["sched"] - ps.outbound["sched"] > window or flight["sched"] < earliest:
                continue
            if outbound_view(flight, t).status in ("Cancelled", "Departed"):
                continue
            found.append(flight)
        return found

    def _next_morning(self, ps: PartyState, flights: list[dict]) -> dict | None:
        morning = (ps.outbound["sched"] + timedelta(days=1)).replace(hour=6, minute=0)
        return next((flight for flight in flights if flight["sched"] >= morning), None)

    def _try_hold(self, ps: PartyState, t: datetime) -> bool:
        flights = self.alternatives(ps, t)
        if ps.party["preference"] == "rest_first":
            morning = self._next_morning(ps, flights)
            if morning:
                flights = [morning] + [flight for flight in flights if flight is not morning]
        cabins = LOWER_CABINS[ps.party["cabin"]]
        passes = [cabins[:1], cabins[1:]] if len(cabins) > 1 else [cabins]
        for cabin_choices in passes:      # same cabin on any flight first, then a lower cabin
            for flight in flights:
                for cabin in cabin_choices:
                    if self.seats.take(flight["key"], cabin, ps.size, t):
                        self._hold_counter += 1
                        expires = ps.assessment.gate_close + timedelta(
                            minutes=self.policy["hold_expiry_after_gate_close_minutes"])
                        ps.hold = {"hold_id": f"H{self._hold_counter:04d}", "flight_key": flight["key"],
                                   "flight_no": flight["flight"], "dep": flight["sched"], "cabin": cabin,
                                   "seat": None, "expires_at": expires}
                        if ps.state == "MONITORING":
                            ps.state = "BACKUP_HELD"
                        self._log(t, "hold", ps, flight=flight["flight"], cabin=cabin)
                        return True
        return False

    def _release_hold(self, ps: PartyState, why: str) -> None:
        if ps.hold:
            self.seats.give_back(ps.hold["flight_key"], ps.hold["cabin"], ps.size)
            self._log(self.t, "hold_released", ps, why=why)
            ps.hold = None

    def _offer_expedite(self, t: datetime, changed: set[str]) -> None:
        """Fast-track or escort for at-risk passengers it helps most; limited capacity (§11.4)."""
        capacity = int(self.policy["expedite_capacity_per_30min"])
        candidates = []
        for ps in self.parties.values():
            if ps.final or ps.expedite_offered or ps.zone != "AT_RISK":
                continue
            fast = assess(ps.in_view.time, ps.in_view.noise, ps.transfer_fast, ps.out_view.time, 0.0, self.config)
            candidates.append((ps.assessment.p_miss - fast.p_miss, ps))
        for gain, ps in sorted(candidates, key=lambda item: (-item[0], item[1].party["party_id"])):
            arrival = ps.in_view.time
            slot = arrival.replace(minute=arrival.minute - arrival.minute % 30, second=0, microsecond=0)
            if gain <= 0.05 or self._expedite_used.get(slot, 0) >= capacity:
                continue
            self._expedite_used[slot] = self._expedite_used.get(slot, 0) + 1
            ps.expedite_offered = True
            changed.add(ps.party["party_id"])

    # ------------------------------------------------------------------ drafts

    def _maybe_draft(self, ps: PartyState, t: datetime) -> bool:
        if ps.final or ps.draft_id or ps.rejected or not ps.hold or ps.state != "BACKUP_HELD":
            return False
        if ps.zone != "WONT_MAKE" and ps.assessment.p_miss < self.policy["tau_offer"]:
            return False
        self._draft_counter += 1
        draft_id = f"D{self._draft_counter:04d}"
        flight = self.flights[ps.hold["flight_key"]]
        # Rounded once, to a whole percent, so the sentence and the field can never disagree.
        chance = round(ps.assessment.p_miss, 2)
        self.drafts[draft_id] = {
            "draft_id": draft_id, "party_id": ps.party["party_id"], "status": "PENDING", "note": None,
            "created": t, "p_miss": chance, "zone": ps.zone,
            "rationale": rationale(
                name=ps.name, cabin=ps.party["cabin"], group_size=ps.size, p_miss=chance,
                out_flight=ps.outbound["flight"],
                driver_text=ps.driver_list[0]["text"] if ps.driver_list else None,
                alt_flight=flight["flight"], alt_dep=flight["sched"],
                alt_arrival=_local(flight.get("dest_sched_arrival")), preference=ps.party["preference"]),
        }
        ps.draft_id, ps.state = draft_id, "DRAFT_PENDING"
        self._log(t, "draft", ps, draft=draft_id)
        return True

    def _close_draft(self, ps: PartyState, note: str) -> None:
        draft = self.drafts.get(ps.draft_id or "")
        if draft and draft["status"] == "PENDING":
            draft["status"], draft["note"] = "REJECTED", note

    def decide(self, draft_id: str, decision: str, note: str | None = None) -> list[dict]:
        """Staff approve or reject one drafted rebooking (non-negotiable 2)."""
        draft = self.drafts.get(draft_id)
        if not draft:
            raise PolicyError(f"Unknown draft {draft_id}.")
        if draft["status"] != "PENDING":
            raise PolicyError(f"Draft {draft_id} is already {draft['status'].lower()}.")
        ps = self.parties[draft["party_id"]]
        events = []
        if decision == "approve":
            draft["status"], draft["note"], ps.state = "APPROVED", note, "OFFERED"
            events.append(self._note(ps, "Your options are ready",
                                     "Choose before you land. Nothing changes unless you choose."))
            events.append({"type": "options_update", "to": "passenger",
                           "pids": [m["pid"] for m in ps.party["members"]],
                           "payload": {"options": self.options(ps.pid)}})
        elif decision == "reject":
            # The backup stays held; nothing changes for the passenger.
            draft["status"], draft["note"], ps.state, ps.rejected = "REJECTED", note, "BACKUP_HELD", True
        else:
            raise PolicyError(f"Unknown decision '{decision}'.")
        self._log(self.t, f"draft_{decision}", ps, draft=draft_id, note=note)
        events.append({"type": "draft_update", "to": "staff", "payload": self.draft_view(draft)})
        events.append({"type": "connection_update", "to": "staff+passenger", "pid": ps.pid,
                       "pids": [m["pid"] for m in ps.party["members"]], "payload": self.status_view(ps)})
        return events

    # ------------------------------------------------------------------ options and choice

    def _approved(self, ps: PartyState) -> bool:
        draft = self.drafts.get(ps.draft_id or "")
        return bool(draft and draft["status"] == "APPROVED")

    def _option(self, ps: PartyState, kind: str, flight: dict, cabin: str, approved: bool) -> dict:
        if kind == "ORIGINAL_EXPEDITE":
            title = f"Stay on {flight['flight']}"
            extras = ["Fast-track transfer", "Escort to the gate"] if ps.expedite_offered else []
        elif kind == "ALT_FLIGHT":
            title = f"Switch to {flight['flight']}"
            extras = ["Seat already held"]
        else:
            title = f"Rest, then fly on {flight['flight']}"
            extras = ["Next-morning departure"]
        return {
            "option_id": f"{ps.party['party_id']}:{kind}", "kind": kind, "title": title,
            "flight": flight["flight"],
            "dep": outbound_view(flight, self.t).time if kind == "ORIGINAL_EXPEDITE" else flight["sched"],
            "final_arrival": _local(flight.get("dest_sched_arrival")),
            "cabin": cabin, "seat": ps.party["seat"] if kind == "ORIGINAL_EXPEDITE" else None,
            "guaranteed": kind != "ORIGINAL_EXPEDITE", "extras": extras, "approved": approved,
            "flight_key": flight["key"],
            "labels": {"flight": "REAL", "dep": "REAL", "final_arrival": "REAL", "cabin": "SYNTHETIC",
                       "seat": "SYNTHETIC", "extras": "ASSUMED"},
        }

    def _options(self, ps: PartyState) -> list[dict]:
        if ps.state in FINAL_STATES and ps.booked:
            flight = self.flights[ps.booked["flight_key"]]
            return [self._option(ps, "ALT_FLIGHT", flight, ps.booked["cabin"], True)]
        found = [self._option(ps, "ORIGINAL_EXPEDITE", ps.outbound, ps.party["cabin"], True)]
        approved = self._approved(ps)
        if ps.hold:
            held = self.flights[ps.hold["flight_key"]]
            found.append(self._option(ps, "ALT_FLIGHT", held, ps.hold["cabin"], approved))
            morning = self._next_morning(ps, self.alternatives(ps, self.t))
            if morning and morning["key"] != held["key"]:
                found.append(self._option(ps, "OVERNIGHT", morning, ps.hold["cabin"], approved))
        order = {"earliest_arrival": ["ORIGINAL_EXPEDITE", "ALT_FLIGHT", "OVERNIGHT"],
                 "rest_first": ["OVERNIGHT", "ALT_FLIGHT", "ORIGINAL_EXPEDITE"]}.get(
                     ps.party["preference"], ["ALT_FLIGHT", "ORIGINAL_EXPEDITE", "OVERNIGHT"])
        return sorted(found, key=lambda option: order.index(option["kind"]))

    def options(self, pid: str) -> list[dict]:
        return [{k: v for k, v in option.items() if k != "flight_key"}
                for option in self._options(self._party(pid))]

    def choose(self, pid: str, option_id: str) -> list[dict]:
        """The passenger picks an option (non-negotiable 3). Only approved options can be booked."""
        ps = self._party(pid)
        if ps.final:
            raise PolicyError("This connection is already settled.")
        option = next((o for o in self._options(ps) if o["option_id"] == option_id), None)
        if not option:
            raise PolicyError(f"Unknown option {option_id}.")
        if option["kind"] != "ORIGINAL_EXPEDITE" and not option["approved"]:
            raise PolicyError("This option has not been approved by staff yet.")
        ps.chosen_kind = option["kind"]
        if option["kind"] == "ORIGINAL_EXPEDITE":
            ps.state, ps.view_key = "PASSENGER_CHOSE", None   # reassess with fast-track if offered
            self._assess(ps, self.t)
        else:
            cabin = option["cabin"]
            if option["kind"] == "OVERNIGHT":
                if not self.seats.take(option["flight_key"], cabin, ps.size, self.t):
                    ps.chosen_kind = None
                    raise PolicyError("That flight no longer has enough seats.")
                self._release_hold(ps, "chose the next-morning flight")
            flight = self.flights[option["flight_key"]]
            seat_rules.release_original_seat(ps, seat_rules.PASSENGER_CHOSE, self.t, ps.assessment.gate_close)
            ps.booked = {"flight_key": flight["key"], "flight_no": flight["flight"], "dep": flight["sched"],
                         "cabin": cabin, "seat": None}
            ps.hold, ps.state = None, "REBOOKED"
        self._log(self.t, "choice", ps, option=option["kind"], flight=option["flight"])
        events = [{"type": "connection_update", "to": "staff+passenger", "pid": ps.pid,
                   "pids": [m["pid"] for m in ps.party["members"]], "payload": self.status_view(ps)}]
        if ps.draft_id:
            events.append({"type": "draft_update", "to": "staff",
                           "payload": self.draft_view(self.drafts[ps.draft_id])})
        return events

    # ------------------------------------------------------------------ views (API payloads)

    def _party(self, pid: str) -> PartyState:
        if pid not in self.by_pid:
            raise PolicyError(f"Unknown passenger {pid}.")
        return self.by_pid[pid]

    def flight_ref(self, flight: dict, view: FlightView) -> dict:
        arrival = flight["kind"] == "arr"
        return {
            "flight": flight["flight"],
            "origin": flight["airport"] if arrival else "HKG",
            "dest": "HKG" if arrival else flight["airport"],
            "origin_city": flight["city"] if arrival else "Hong Kong",
            "dest_city": "Hong Kong" if arrival else flight["city"],
            "sched": flight["sched"], "est": view.est, "actual": view.actual,
            "stand": flight.get("stand"), "gate": flight.get("gate"), "status": view.status,
            "origin_departure": _local(flight.get("origin_sched_departure")),
            "dest_arrival": _local(flight.get("dest_sched_arrival")),
            "labels": {"sched": "REAL", "est": "REAL", "actual": "REAL", "stand": "REAL", "gate": "REAL",
                       "status": "REAL", "origin_departure": "REAL", "dest_arrival": "REAL"},
        }

    def status_view(self, ps: PartyState) -> dict:
        a = ps.assessment
        hold = None
        shown = ps.hold or (ps.booked if ps.state == "REBOOKED" else None)
        if shown:
            hold = {"hold_id": shown.get("hold_id", "BOOKED"), "flight": shown["flight_no"], "dep": shown["dep"],
                    "cabin": shown["cabin"], "seat": shown.get("seat"),
                    "expires_at": shown.get("expires_at", shown["dep"])}
        return {
            "connection_id": ps.party["party_id"], "pid": ps.pid, "passenger_name": ps.name,
            "cabin": ps.party["cabin"], "group_size": ps.size, "assistance": ps.party["assistance"],
            "tier": ps.party["tier"], "t": self.t,
            "inbound": self.flight_ref(ps.inbound, ps.in_view),
            "outbound": self.flight_ref(ps.outbound, ps.out_view),
            "gate_close": a.gate_close,
            "ready_at_gate": {"p10": a.ready_p10, "p50": a.ready_p50, "p90": a.ready_p90},
            "minutes_available": a.minutes_available, "minutes_needed": list(a.minutes_needed),
            "p_miss": round(a.p_miss, 3), "zone": ps.zone, "state": ps.state,
            "drivers": ps.driver_list, "backup_hold": hold, "expedite_offered": ps.expedite_offered,
            "original_seat_held": ps.original_seat_held, "outcome": ps.outcome,
            # Missed with no seat held (every later flight full): staff must rebook by hand.
            "needs_manual_rebooking": ps.outcome == "MISSED" and ps.state != "REBOOKED",
            "labels": {"p_miss": "SIMULATED", "zone": "SIMULATED", "ready_at_gate": "SIMULATED",
                       "minutes_available": "SIMULATED", "minutes_needed": "ASSUMED",
                       "gate_close": "REAL", "drivers": "SIMULATED", "backup_hold": "ASSUMED",
                       "expedite_offered": "ASSUMED", "passenger_name": "SYNTHETIC", "cabin": "SYNTHETIC",
                       "group_size": "SYNTHETIC", "tier": "SYNTHETIC", "assistance": "SYNTHETIC",
                       "outcome": "SIMULATED", "needs_manual_rebooking": "SIMULATED"},
        }

    def draft_view(self, draft: dict) -> dict:
        ps = self.parties[draft["party_id"]]
        held = ps.hold or ps.booked
        flight = self.flights[held["flight_key"]] if held else ps.outbound
        option = self._option(ps, "ALT_FLIGHT", flight, held["cabin"] if held else ps.party["cabin"],
                              draft["status"] == "APPROVED")
        option.pop("flight_key")
        return {
            "draft_id": draft["draft_id"], "connection_id": ps.party["party_id"], "pid": ps.pid,
            "passenger_name": ps.name, "cabin": ps.party["cabin"], "group_size": ps.size,
            "assistance": ps.party["assistance"], "tier": ps.party["tier"],
            "p_miss": draft["p_miss"], "zone": draft["zone"],
            "inbound_flight": ps.inbound["flight"], "outbound_flight": ps.outbound["flight"],
            "option": option, "rationale": draft["rationale"], "status": draft["status"],
            "note": draft["note"],
            "labels": {"p_miss": "SIMULATED", "rationale": "SIMULATED", "passenger_name": "SYNTHETIC",
                       "cabin": "SYNTHETIC", "group_size": "SYNTHETIC", "tier": "SYNTHETIC"},
        }

    def trip(self, pid: str) -> dict:
        ps = self._party(pid)
        member = next(m for m in ps.party["members"] if m["pid"] == pid)
        return {
            "passenger": {"pid": pid, "name": member["name"], "cabin": ps.party["cabin"],
                          "seat": ps.party["seat"], "tier": ps.party["tier"], "group_size": ps.size,
                          "assistance": ps.party["assistance"], "preference": ps.party["preference"],
                          "is_synthetic": True,
                          "labels": {field: "SYNTHETIC" for field in
                                     ("name", "cabin", "seat", "tier", "group_size", "assistance", "preference")}},
            "inbound": self.flight_ref(ps.inbound, ps.in_view),
            "outbound": self.flight_ref(ps.outbound, ps.out_view),
            "sched_gap_min": ps.party["sched_gap_min"],
            "labels": {"sched_gap_min": "REAL"},
        }

    def wave(self, start: datetime | None = None, end: datetime | None = None) -> dict:
        """Every connecting passenger who is not plainly safe, plus totals per inbound flight."""
        rows, inbounds, totals = [], {}, {"SAFE": 0, "AT_RISK": 0, "WONT_MAKE": 0}
        for ps in self.parties.values():
            if (start and ps.inbound["sched"] < start) or (end and ps.inbound["sched"] > end):
                continue
            totals[ps.zone] += ps.size
            entry = inbounds.setdefault(ps.inbound["key"], {"flight": ps.inbound, "view": ps.in_view,
                                                            "connecting": 0, "AT_RISK": 0, "WONT_MAKE": 0})
            entry["connecting"] += ps.size
            if ps.zone != "SAFE":
                entry[ps.zone] += ps.size
            # Listed: anyone at risk, and anyone with a hold, draft, offer or rebooking in play.
            if ps.zone != "SAFE" or ps.state not in ("MONITORING", "MADE_ORIGINAL"):
                rows.append(ps)
        rows.sort(key=lambda ps: (-ps.assessment.p_miss, ps.party["party_id"]))
        inbound_list = []
        for entry in sorted(inbounds.values(), key=lambda e: e["flight"]["sched"]):
            flight, view = entry["flight"], entry["view"]
            known = view.actual or (view.est if view.source != "schedule" else None)
            inbound_list.append({
                "flight": flight["flight"], "origin": flight["airport"], "origin_city": flight["city"],
                "sched": flight["sched"], "est": view.est, "actual": view.actual, "status": view.status,
                "delay_min": int(round((known - flight["sched"]).total_seconds() / 60)) if known else None,
                "stand": flight.get("stand"), "connecting": entry["connecting"],
                "at_risk": entry["AT_RISK"], "wont_make": entry["WONT_MAKE"],
                "labels": {"sched": "REAL", "est": "REAL", "actual": "REAL", "delay_min": "REAL",
                           "stand": "REAL", "connecting": "SYNTHETIC", "at_risk": "SIMULATED",
                           "wont_make": "SIMULATED"},
            })
        states = [ps.state for ps in self.parties.values()]
        summary = {
            "t": self.t, "connecting": sum(ps.size for ps in self.parties.values()),
            "safe": totals["SAFE"], "at_risk": totals["AT_RISK"], "wont_make": totals["WONT_MAKE"],
            "holds": sum(1 for ps in self.parties.values() if ps.hold), "peak_holds": self.peak_holds,
            "drafts_pending": sum(1 for d in self.drafts.values() if d["status"] == "PENDING"),
            "drafts_approved": sum(1 for d in self.drafts.values() if d["status"] == "APPROVED"),
            "rebooked": states.count("REBOOKED"), "made_original": states.count("MADE_ORIGINAL"),
            "needs_manual_rebooking": sum(ps.size for ps in self.parties.values()
                                          if ps.outcome == "MISSED" and ps.state != "REBOOKED"),
            "inbounds": inbound_list,
            "labels": {"connecting": "SYNTHETIC", "safe": "SIMULATED", "at_risk": "SIMULATED",
                       "wont_make": "SIMULATED", "holds": "SIMULATED", "peak_holds": "SIMULATED",
                       "drafts_pending": "SIMULATED", "drafts_approved": "SIMULATED",
                       "rebooked": "SIMULATED", "made_original": "SIMULATED",
                       "needs_manual_rebooking": "SIMULATED"},
        }
        return {"summary": summary, "connections": [self.status_view(ps) for ps in rows]}

    def draft_list(self, status: str | None = None) -> list[dict]:
        found = [self.draft_view(d) for d in self.drafts.values() if not status or d["status"] == status]
        return sorted(found, key=lambda d: (-d["p_miss"], d["draft_id"]))

    # ------------------------------------------------------------------ helpers

    def _note(self, ps: PartyState, title: str, body: str) -> dict:
        return {"type": "notification", "to": "passenger", "pids": [m["pid"] for m in ps.party["members"]],
                "payload": {"title": title, "body": body}}

    def _log(self, t: datetime, kind: str, ps: PartyState, **details) -> None:
        self.log.append({"t": t.isoformat(), "kind": kind, "party": ps.party["party_id"], **details})


def _local(value: str | None) -> datetime | None:
    """A destination-local time like 2026-10-23T12:15 (no offset: it is local there)."""
    return datetime.fromisoformat(value) if value else None
