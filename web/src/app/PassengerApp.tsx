// The passenger phone (/app): which screen shows when, fed live by the WebSocket. The top bar and the
// bottom navigation are fixed; only the middle scrolls.
import { useCallback, useEffect, useState } from "react";
import { api, type ConnectionStatus, type Trip } from "../api/client";
import { useLive, type LiveMessage } from "../api/live";
import { buildStory, clock, type Stage, type Story } from "./flow/journey";
import {
  AirportScreen, ArriveScreen, BagsScreen, FlyingScreen, HomeScreen, InsideScreen, LeaveScreen, LockScreen,
  RebookedScreen, SettingsScreen,
} from "./flow/screens";
import { PlannerScreen } from "./flow/tools";
import { BottomNav, PhoneFrame, StatusBar, TopBar } from "./flow/ui";

type Screen = "home" | "trips" | "bags" | "settings" | "tools" | Stage;

// Demo only: jump the replay to a moment of the story and open the matching screen (the Figma frames).
const DEMO: { label: string; t: string; screen: Screen; rebook?: boolean; lock?: boolean }[] = [
  { label: "CGK airport, before check-in", t: "2026-12-15T07:10:00+08:00", screen: "airport" },
  { label: "CGK airport, after check-in", t: "2026-12-15T07:31:00+08:00", screen: "insideOrigin" },
  { label: "Rebooked: lock-screen alert", t: "2026-12-15T13:46:00+08:00", screen: "rebooked", rebook: true, lock: true },
  { label: "Rebooked: new connection", t: "2026-12-15T13:50:00+08:00", screen: "rebooked", rebook: true },
  { label: "Bags loaded in Hong Kong", t: "2026-12-15T23:30:00+08:00", screen: "bags" },
  { label: "Bags arriving in London", t: "2026-12-16T14:20:00+08:00", screen: "bags" },
  { label: "Arriving: to the hotel", t: "2026-12-16T14:00:00+08:00", screen: "arrive" },
];
type Alert = { title: string; body: string };

function tripScreen(s: Story, stage: Stage) {
  switch (stage) {
    case "leave": return <LeaveScreen s={s} />;
    case "airport": return <AirportScreen s={s} />;
    case "insideOrigin": return <InsideScreen s={s} place="origin" />;
    case "flying": return <FlyingScreen s={s} />;
    case "rebooked": return <RebookedScreen s={s} />;
    case "insideHkg": return <InsideScreen s={s} place="hkg" />;
    case "onward": return <BagsScreen s={s} />;
    case "arrive": return <ArriveScreen s={s} exit={false} />;
    default: return <ArriveScreen s={s} exit />;
  }
}

export function PassengerApp() {
  const [pid, setPid] = useState<string | null>(new URLSearchParams(location.search).get("pid"));
  const [trip, setTrip] = useState<Trip | null>(null);
  const [status, setStatus] = useState<ConnectionStatus | null>(null);
  const [screen, setScreen] = useState<Screen>("home");
  const [history, setHistory] = useState<Screen[]>([]);
  const [alert, setAlert] = useState<Alert | null>(null);
  const [menu, setMenu] = useState(false);
  const [demo, setDemo] = useState(false);
  const [jumping, setJumping] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!pid) api.replayState().then((state) => setPid(state.hero_pid)).catch(() => setError("The demo server is not answering."));
  }, [pid]);

  const refresh = useCallback(async () => {
    if (!pid) return;
    try {
      const [nextTrip, nextStatus] = await Promise.all([api.trip(pid), api.protect(pid)]);
      setTrip(nextTrip);
      setStatus(nextStatus);
      setError(null);
    } catch {
      setError("Couldn't load your trip. Retrying.");
    }
  }, [pid]);
  useEffect(() => { refresh(); }, [refresh]);

  const onMessage = useCallback((message: LiveMessage) => {
    if (message.type === "reload") refresh();
    else if (message.type === "connection_update" && message.payload?.connection_id) {
      setStatus((previous) => (previous && previous.connection_id === message.payload.connection_id
        ? { ...message.payload, pid: previous.pid } : previous));
      if (pid) api.trip(pid).then(setTrip).catch(() => undefined);
    } else if (message.type === "notification") setAlert(message.payload);
  }, [pid, refresh]);
  const { clock: replay } = useLive(pid ? `role=passenger&pid=${pid}` : "role=passenger", onMessage);
  const nowIso = replay?.t ?? status?.t ?? new Date().toISOString();

  if (!trip || !status) {
    return <PhoneFrame><div className="m-auto p-6 text-center text-[15px] text-muted">{error ?? "Loading your trip…"}</div></PhoneFrame>;
  }

  const s = buildStory(trip, status, nowIso);
  const go = (next: Screen) => { setHistory((h) => [...h, screen]); setScreen(next); setMenu(false); };
  const back = () => { setScreen(history[history.length - 1] ?? "home"); setHistory((h) => h.slice(0, -1)); };
  const time = clock(s.now);
  const nav = screen === "home" ? "home" : screen === "tools" ? "tools" : "trips";
  const preview = () => {
    setMenu(false);
    setAlert(s.rebooked
      ? { title: "Your connection has changed", body: `${status.inbound.flight} lands after ${status.outbound.flight} closes, so we've moved you to ${s.onward.flight}. Tap for details.` }
      : { title: "Cathay Flow is on", body: `We're watching your connection to ${status.outbound.flight}.` });
  };

  const jump = async (item: (typeof DEMO)[number]) => {
    setJumping(true);
    try {
      await api.control("pause");
      await api.control("seek", { t: item.t });
      let next = await api.protect(status.pid);
      if (item.rebook && next.state === "DRAFT_PENDING" && next.draft_id) {
        await api.decide(next.draft_id, "approve");
        next = await api.protect(status.pid);
      }
      setStatus(next);
      setTrip(await api.trip(status.pid));
      setHistory([]);
      setScreen(item.screen);
      setAlert(item.lock ? { title: "Your connection has changed",
        body: `${next.inbound.flight} lands after ${next.outbound.flight} closes, so we've moved you${next.companions.length ? ` and ${next.companions[0].split(" ")[0]}` : ""} to ${next.alternative?.flight ?? ""} tonight. ${next.companions.length ? "Seats together, bags moved." : "Bags moved."} Tap for details.` } : null);
      setDemo(false);
    } catch {
      setError("Couldn't jump to that moment.");
    } finally {
      setJumping(false);
    }
  };

  let body;
  if (screen === "home") {
    body = <HomeScreen s={s} onFlow={() => go("trips")} onBags={() => go("bags")} onMenu={() => go("settings")} onBell={preview} />;
  } else if (screen === "settings") body = <SettingsScreen s={s} />;
  else if (screen === "tools") body = <div className="pt-3"><PlannerScreen nowIso={nowIso} /></div>;
  else if (screen === "bags") body = <BagsScreen s={s} />;
  else body = tripScreen(s, screen === "trips" ? s.stage : screen);

  return (
    <PhoneFrame>
      {screen === "home"
        ? <div className="pointer-events-none absolute inset-x-0 top-0 z-20 bg-transparent"><StatusBar time={time} light /></div>
        : <TopBar time={time} title={screen === "tools" ? "Gate Planner" : screen === "settings" ? "Cathay Flow" : "Cathay Flow"} onBack={back} />}
      <main className={`no-scrollbar relative flex-1 overflow-y-auto overscroll-contain ${screen === "settings" ? "" : "pb-[24px]"}`}>
        {body}
        {error && <p className="mx-4 mt-3 rounded-[8px] bg-warn px-3 py-2 text-[13px] text-warn-text">{error}</p>}
      </main>
      <BottomNav active={nav} onHome={() => go("home")} onTrips={() => go("trips")} onTools={() => go("tools")} />
      {menu && (
        <div className="absolute inset-0 z-30" onClick={() => setMenu(false)}>
          <div className="absolute right-3 top-[150px] w-[230px] overflow-hidden rounded-[12px] bg-white text-[14px] text-ink shadow-xl">
            {([["Settings", () => go("settings")], ["Your bags", () => go("bags")], ["Preview lock-screen alert", preview]] as const).map(([label, action]) => (
              <button key={label} onClick={action} className="block w-full border-b border-line px-4 py-3 text-left last:border-0 hover:bg-info">{label}</button>
            ))}
          </div>
        </div>
      )}
      <button onClick={() => setDemo((d) => !d)} aria-label="Demo states"
        className="absolute bottom-[96px] right-[12px] z-30 rounded-full bg-black/70 px-[12px] py-[6px] font-sans text-[12px] font-semibold text-white shadow-lg">
        Demo
      </button>
      {demo && (
        <div className="absolute inset-0 z-30 flex items-end bg-black/30" onClick={() => setDemo(false)}>
          <div className="w-full rounded-t-[18px] bg-white px-4 pb-6 pt-4 font-sans" onClick={(e) => e.stopPropagation()}>
            <div className="mb-2 text-[13px] font-bold text-muted">Demo: jump to a moment</div>
            {DEMO.map((item) => (
              <button key={item.label} disabled={jumping} onClick={() => jump(item)}
                className="block w-full border-b border-line py-[11px] text-left text-[15px] text-ink last:border-0 disabled:opacity-40">{item.label}</button>
            ))}
            <button disabled={jumping} onClick={() => { setDemo(false); go("settings"); }}
              className="block w-full py-[11px] text-left text-[15px] text-ink">Settings (Personalise Flow)</button>
          </div>
        </div>
      )}
      {alert && <LockScreen s={s} title={alert.title} body={alert.body} onOpen={() => { setAlert(null); go("trips"); }} onClose={() => setAlert(null)} />}
    </PhoneFrame>
  );
}
