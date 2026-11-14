"""Runtime state: the one simulation, the replay clock and the open WebSockets (AGENTS.md §4).

Everything runs on the event loop of a single process, so staff approvals and passenger choices
see the same state. A second process would split them: run exactly one task.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder

from app.replay.sim import Sim
from flowcore.scenario import list_scenarios


class Hub:
    """Open sockets by role. Staff see everything; a passenger sees their own party."""

    def __init__(self) -> None:
        self.sockets: dict[WebSocket, tuple[str, str | None]] = {}

    def add(self, socket: WebSocket, role: str, pid: str | None) -> None:
        self.sockets[socket] = (role, pid)

    def remove(self, socket: WebSocket) -> None:
        self.sockets.pop(socket, None)

    def _wants(self, role: str, pid: str | None, event: dict) -> bool:
        to = event.get("to", "all")
        if to == "all":
            return True
        if role == "staff":
            return "staff" in to
        return "passenger" in to and pid in (event.get("pids") or [event.get("pid")])

    async def send(self, event: dict, t: datetime | None) -> None:
        message = jsonable_encoder({"type": event["type"], "t": t, "payload": event.get("payload", {})})
        for socket, (role, pid) in list(self.sockets.items()):
            if not self._wants(role, pid, event):
                continue
            try:
                await socket.send_json(message)
            except Exception:
                self.remove(socket)


class Runtime:
    def __init__(self, scenario_id: str | None, tick_seconds: float, clock_seconds: float,
                 ping_seconds: float) -> None:
        self.hub = Hub()
        self.sim: Sim | None = Sim(scenario_id) if scenario_id else None
        self.playing = False
        self.speed = 60.0                 # simulated seconds per real second: one minute a second
        self.tick_seconds = tick_seconds
        self.clock_seconds = clock_seconds
        self.ping_seconds = ping_seconds
        self._task: asyncio.Task | None = None

    @staticmethod
    def default_scenario(wanted: str | None) -> str | None:
        """The scenario asked for (FLOW_SCENARIO), else the one marked as the demo story, else the first."""
        found = list_scenarios()
        ids = [item["id"] for item in found]
        if wanted in ids:
            return wanted
        return next((item["id"] for item in found if item.get("default")), ids[0] if ids else None)

    def load(self, scenario_id: str) -> None:
        self.sim, self.playing = Sim(scenario_id), False

    def replay_state(self) -> dict:
        sim = self.sim
        return {"scenario_id": sim.meta["id"], "t": sim.t, "speed": self.speed, "playing": self.playing,
                "start": sim.start, "end": sim.end, "hero_pid": sim.meta["hero_pid"],
                "illustrative": bool(sim.meta.get("illustrative"))}

    async def publish(self, events: list[dict]) -> None:
        for event in events:
            await self.hub.send(event, self.sim.t if self.sim else None)

    async def publish_clock(self) -> None:
        payload = self.replay_state() if self.sim else {}
        await self.hub.send({"type": "clock", "payload": payload}, self.sim.t if self.sim else None)

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        last_clock = last_ping = time.monotonic()
        while True:
            await asyncio.sleep(self.tick_seconds)
            now = time.monotonic()
            if self.sim and self.playing:
                target = self.sim.t + timedelta(seconds=self.speed * self.tick_seconds)
                events = self.sim.advance_to(target)
                if self.sim.t >= self.sim.end:
                    self.playing = False
                await self.publish(events)
                await self.publish_clock()
                last_clock = now
            elif now - last_clock >= self.clock_seconds:
                await self.publish_clock()
                last_clock = now
            if now - last_ping >= self.ping_seconds:
                await self.hub.send({"type": "ping"}, None)
                last_ping = now
