"""HTTP endpoints (AGENTS.md §10.2). All handlers are async so they run on the event loop,
next to the replay clock, and never race the simulation."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

import asyncio
from dataclasses import asdict

from app import planner, schemas
from flowcore.engine.gate_planner import PlanRequest, plan
from app.replay.sim import PolicyError
from app.state import Runtime
from flowcore.config import find_repo_root
from flowcore.scenario import list_scenarios


def build_router(runtime: Runtime) -> APIRouter:
    router = APIRouter(prefix="/api")

    def sim():
        if runtime.sim is None:
            raise HTTPException(503, "No scenario is loaded.")
        return runtime.sim

    def refuse(err: PolicyError) -> HTTPException:
        text = str(err)
        return HTTPException(404 if text.startswith("Unknown") else 409, text)

    # ---- replay

    @router.get("/scenarios", response_model=list[schemas.ScenarioInfo])
    async def scenarios():
        return list_scenarios()

    @router.post("/replay/load", response_model=schemas.ReplayState)
    async def replay_load(body: schemas.ReplayLoad):
        if body.scenario_id not in [item["id"] for item in list_scenarios()]:
            raise HTTPException(404, f"Unknown scenario {body.scenario_id}.")
        runtime.load(body.scenario_id)
        await runtime.publish([{"type": "reload", "to": "all"}])
        return runtime.replay_state()

    @router.post("/replay/control", response_model=schemas.ReplayState)
    async def replay_control(body: schemas.ReplayControl):
        s = sim()
        events: list[dict] = []
        if body.action == "play":
            runtime.playing = s.t < s.end
        elif body.action == "pause":
            runtime.playing = False
        elif body.action == "speed":
            if not body.speed or body.speed <= 0:
                raise HTTPException(422, "speed must be a positive number.")
            runtime.speed = min(body.speed, 3600.0)
        elif body.action == "seek":
            if body.t is None:
                raise HTTPException(422, "seek needs t.")
            runtime.playing = False
            events = s.seek(body.t)
        elif body.action == "reset":
            runtime.playing = False
            s.reset()
            events = [{"type": "reload", "to": "all"}]
        await runtime.publish(events)
        await runtime.publish_clock()
        return runtime.replay_state()

    @router.get("/replay/state", response_model=schemas.ReplayState)
    async def replay_state():
        sim()
        return runtime.replay_state()

    # ---- passenger

    @router.get("/passengers/{pid}/trip", response_model=schemas.Trip)
    async def trip(pid: str):
        try:
            return sim().trip(pid)
        except PolicyError as err:
            raise refuse(err) from err

    @router.get("/passengers/{pid}/protect", response_model=schemas.ConnectionStatus)
    async def protect(pid: str):
        s = sim()
        if pid not in s.by_pid:
            raise HTTPException(404, f"Unknown passenger {pid}.")
        return {**s.status_view(s.by_pid[pid]), "pid": pid}

    @router.get("/passengers/{pid}/options", response_model=list[schemas.Option])
    async def options(pid: str):
        try:
            return sim().options(pid)
        except PolicyError as err:
            raise refuse(err) from err

    @router.post("/passengers/{pid}/choose", response_model=schemas.ConnectionStatus)
    async def choose(pid: str, body: schemas.ChooseRequest):
        s = sim()
        try:
            events = s.choose(pid, body.option_id)
        except PolicyError as err:
            raise refuse(err) from err
        await runtime.publish(events)
        return {**s.status_view(s.by_pid[pid]), "pid": pid}

    # ---- staff

    @router.get("/staff/wave", response_model=schemas.Wave)
    async def wave(start: datetime | None = Query(None, alias="from"),
                   end: datetime | None = Query(None, alias="to")):
        return sim().wave(start, end)

    @router.get("/staff/drafts", response_model=list[schemas.Draft])
    async def drafts(status: str | None = None):
        return sim().draft_list(status)

    # Declared before the {draft_id} route so "approve-batch" is not read as an id.
    @router.post("/staff/drafts/approve-batch", response_model=list[schemas.Draft])
    async def approve_batch(body: schemas.ApproveBatch):
        s = sim()
        events, done = [], []
        for draft_id in body.ids:
            try:
                events += s.decide(draft_id, "approve")
                done.append(draft_id)
            except PolicyError:
                continue      # already decided or gone: skip it, approve the rest
        await runtime.publish(events)
        return [s.draft_view(s.drafts[draft_id]) for draft_id in done]

    @router.post("/staff/drafts/{draft_id}", response_model=schemas.Draft)
    async def decide(draft_id: str, body: schemas.DraftDecision):
        s = sim()
        try:
            events = s.decide(draft_id, body.decision, body.note)
        except PolicyError as err:
            raise refuse(err) from err
        await runtime.publish(events)
        return s.draft_view(s.drafts[draft_id])

    # ---- gate planner

    @router.get("/planner/options", response_model=schemas.PlannerOptions)
    async def planner_options():
        s = sim()
        return {"t": s.t, "origins": [{"id": o["id"], "name": o["name"]} for o in planner.origins()],
                "flights": planner.flight_choices(s.flights, s.t)}

    @router.post("/planner/plan", response_model=schemas.PlannerResult)
    async def planner_plan(body: schemas.PlannerRequest):
        s = sim()
        flight = s.flights.get(body.flight_key)
        if not flight or flight["kind"] != "dep":
            raise HTTPException(404, f"Unknown departure {body.flight_key}.")
        try:
            planner.origin(body.origin_id)
        except KeyError:
            raise HTTPException(404, f"Unknown starting point {body.origin_id}.") from None
        request = PlanRequest(**body.model_dump())
        road = planner.road_for(body.origin_id, body.mode, s.config)
        # Road lookups may call Google: keep them off the event loop.
        result = await asyncio.to_thread(plan, request, flight, s.t, s.config, s.zones, road, s.seed)
        return {**asdict(result), "t": s.t,
                "labels": {"departure": "REAL", "gate": "REAL", "deadline": "ASSUMED", "leave_by": "SIMULATED",
                           "typical_total": "SIMULATED", "upper_total": "SIMULATED"}}

    # ---- impact

    @router.get("/impact", response_model=list[schemas.ImpactMetric])
    async def impact():
        file = find_repo_root() / "data" / "evidence.json"
        return json.loads(file.read_text(encoding="utf-8")) if file.is_file() else []

    return router
