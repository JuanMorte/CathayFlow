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

  let body;
  if (screen === "home") {
    body = <HomeScreen s={s} onFlow={() => go("trips")} onBags={() => go("bags")} onMenu={() => setMenu(true)} onBell={preview} />;
  } else if (screen === "settings") body = <SettingsScreen s={s} />;
  else if (screen === "tools") body = <div className="pt-3"><PlannerScreen nowIso={nowIso} /></div>;
  else if (screen === "bags") body = <BagsScreen s={s} />;
  else body = tripScreen(s, screen === "trips" ? s.stage : screen);

  return (
    <PhoneFrame>
      {screen === "home"
        ? <div className="relative z-20 shrink-0 sm:bg-transparent"><StatusBar time={time} light /></div>
        : <TopBar time={time} title={screen === "tools" ? "Gate Planner" : screen === "settings" ? "Cathay Flow" : "Cathay Flow"} onBack={back} />}
      <main className="relative flex-1 overflow-y-auto pb-[24px]">
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
      {alert && <LockScreen s={s} title={alert.title} body={alert.body} onOpen={() => { setAlert(null); go("trips"); }} onClose={() => setAlert(null)} />}
    </PhoneFrame>
  );
}
