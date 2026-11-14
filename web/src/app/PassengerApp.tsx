// The passenger phone (/app): which screen shows when, fed live by the WebSocket.
import { useCallback, useEffect, useState } from "react";
import { api, type ConnectionStatus, type Option, type Trip } from "../api/client";
import { useLive, type LiveMessage } from "../api/live";
import { ArriveScreen } from "./flow/arrive";
import { BagsScreen } from "./flow/bags";
import { ConfirmSheet, ConnectScreen } from "./flow/connect";
import { HomeScreen, LockAlert, SetupScreen, type Alert } from "./flow/home";
import { buildView, clock, shortDate, strip, type View } from "./flow/journey";
import { BottomNav, Header, JourneyStrip, PhoneFrame, SampleNote } from "./flow/kit";
import { NavigateScreen } from "./flow/navigate";
import { PlanBScreen } from "./flow/planb";
import { PrepareScreen } from "./flow/prepare";
import { PlannerScreen } from "./flow/tools";

type Screen = "home" | "hkg" | "prepare" | "arrive" | "bags" | "setup" | "tools";

export function PassengerApp() {
  const [pid, setPid] = useState<string | null>(new URLSearchParams(location.search).get("pid"));
  const [trip, setTrip] = useState<Trip | null>(null);
  const [status, setStatus] = useState<ConnectionStatus | null>(null);
  const [options, setOptions] = useState<Option[]>([]);
  const [screen, setScreen] = useState<Screen>("home");
  const [alert, setAlert] = useState<Alert | null>(null);
  const [menu, setMenu] = useState(false);
  const [confirming, setConfirming] = useState<Option | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // The hero comes from the replay unless the URL names a passenger.
  useEffect(() => {
    if (!pid) api.replayState().then((state) => setPid(state.hero_pid)).catch(() => setError("The demo server is not answering."));
  }, [pid]);

  const refresh = useCallback(async () => {
    if (!pid) return;
    try {
      const [nextTrip, nextStatus, nextOptions] = await Promise.all([api.trip(pid), api.protect(pid), api.options(pid)]);
      setTrip(nextTrip);
      setStatus(nextStatus);
      setOptions(nextOptions);
      setError(null);
    } catch {
      setError("Couldn't load your trip. Retrying.");
    }
  }, [pid]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const onMessage = useCallback((message: LiveMessage) => {
    if (message.type === "reload") refresh();
    else if (message.type === "connection_update" && message.payload?.connection_id) {
      setStatus((previous) => (previous && previous.connection_id === message.payload.connection_id
        ? { ...message.payload, pid: previous.pid } : previous));
      if (pid) api.options(pid).then(setOptions).catch(() => undefined);
    } else if (message.type === "options_update") setOptions(message.payload.options);
    else if (message.type === "notification") setAlert(message.payload);
  }, [pid, refresh]);

  const { clock: replay } = useLive(pid ? `role=passenger&pid=${pid}` : "role=passenger", onMessage);
  const nowIso = replay?.t ?? status?.t ?? new Date().toISOString();

  const choose = async (option: Option) => {
    if (!pid) return;
    setBusy(true);
    try {
      setStatus(await api.choose(pid, option.option_id));
      setOptions(await api.options(pid));
      setScreen("hkg");
    } catch (err) {
      setError(err instanceof Error ? err.message : "That didn't work.");
    } finally {
      setBusy(false);
    }
  };

  if (!trip || !status) {
    return (
      <PhoneFrame>
        <div className="m-auto p-6 text-center text-[15px] text-muted">{error ?? "Loading your trip…"}</div>
      </PhoneFrame>
    );
  }

  const view = buildView(trip, status, options, nowIso);
  const open = (next: string) => setScreen(next as Screen);
  const time = clock(view.now);
  const lockPreview = () => {
    setMenu(false);
    setAlert(view.status.backup_hold
      ? { title: "Tight connection in Hong Kong",
          body: `${status.inbound.flight} now lands ${clock(view.inboundAt)}. We've already held a backup seat for you, just in case.` }
      : { title: "Cathay Flow is on", body: `We're watching your connection to ${status.outbound.flight}.` });
  };

  let body: JSX.Element;
  if (screen === "home") {
    body = (
      <div className="flex-1 overflow-y-auto">
        <HomeScreen view={view} onOpenFlow={() => setScreen("hkg")} onMenu={() => setMenu(true)} />
      </div>
    );
  } else if (screen === "tools") {
    body = (
      <>
        <Header time={time} title="Gate Planner" subtitle="Leaving from Hong Kong" onBack={() => setScreen("home")}
          onMenu={() => setMenu(true)} />
        <div className="-mt-3 flex-1 overflow-y-auto pb-1"><PlannerScreen nowIso={nowIso} /><SampleNote /></div>
      </>
    );
  } else if (screen === "setup") {
    body = (
      <>
        <Header time={time} title="Set up Cathay Flow" close onBack={() => setScreen("home")}
          subtitle={`${status.inbound.origin_city} → ${status.outbound.dest_city} · ${shortDate(view.originDeparture, view.originZone)}`}
          right={<span className="w-9" />} />
        <div className="-mt-3 flex-1 overflow-y-auto"><SetupScreen view={view} onDone={() => setScreen("home")} /></div>
      </>
    );
  } else {
    const { title, subtitle, content, at } = journeyScreen(view, screen, {
      choose, busy, onBags: () => setScreen("bags"), onSwitch: (option) => setConfirming(option),
    });
    const s = strip(view, open, at);
    body = (
      <>
        <Header time={time} title={title} subtitle={subtitle} onBack={() => setScreen(screen === "hkg" ? "home" : "hkg")}
          onMenu={() => setMenu(true)}>
          <JourneyStrip stops={s.stops} done={s.done} here={s.here} progress={s.progress} flying={s.flying} />
        </Header>
        <div className="flex-1 overflow-y-auto pb-1">
          {content}
          {error && <p className="mx-4 mt-3 rounded-[8px] bg-warn px-3 py-2 text-[13px] text-warn-text">{error}</p>}
          <SampleNote />
        </div>
      </>
    );
  }

  return (
    <PhoneFrame>
      {body}
      {screen !== "setup" && (
        <BottomNav active={screen === "home" ? "home" : screen === "tools" ? "tools" : "trips"}
          onHome={() => setScreen("home")} onTrips={() => setScreen("hkg")} onTools={() => setScreen("tools")} />
      )}
      {menu && (
        <div className="absolute inset-0 z-30" onClick={() => setMenu(false)}>
          <div className="absolute right-3 top-[90px] w-[230px] overflow-hidden rounded-[12px] bg-white text-[14px] text-ink shadow-xl sm:top-[100px]">
            {[["Preview lock-screen alert", lockPreview], ["Your bags", () => { setMenu(false); setScreen("bags"); }],
              ["Set up Cathay Flow", () => { setMenu(false); setScreen("setup"); }]].map(([label, action]) => (
              <button key={label as string} onClick={action as () => void} className="block w-full border-b border-line px-4 py-3 text-left last:border-0 hover:bg-info">
                {label as string}
              </button>
            ))}
          </div>
        </div>
      )}
      {confirming && (
        <ConfirmSheet view={view} option={confirming} busy={busy} onCancel={() => setConfirming(null)}
          onConfirm={() => { choose(confirming); setConfirming(null); }} />
      )}
      {alert && (
        <LockAlert view={view} alert={alert} onOpen={() => { setAlert(null); setScreen("hkg"); }} onClose={() => setAlert(null)} />
      )}
    </PhoneFrame>
  );
}

function journeyScreen(view: View, screen: Screen, actions: {
  choose: (option: Option) => void; busy: boolean; onBags: () => void; onSwitch: (option: Option) => void;
}): { title: string; subtitle: string; content: JSX.Element; at?: "arrive" } {
  const { status } = view;
  const route = `${status.inbound.origin_city} → ${status.outbound.dest_city} · ${shortDate(view.originDeparture, view.originZone)}`;
  if (screen === "prepare") return { title: "Your journey", subtitle: route, content: <PrepareScreen view={view} /> };
  if (screen === "bags") {
    const n = view.sample.bags.length;
    return { title: "Your bags", subtitle: `Bag Intelligence · ${n === 1 ? "one bag" : `${n} bags`} to ${status.outbound.dest_city}`, content: <BagsScreen view={view} /> };
  }
  if (screen === "arrive") {
    return { title: "Arrival Mode", subtitle: `${status.outbound.dest_city} · ${view.sample.destinationTerminal}`, content: <ArriveScreen view={view} />, at: "arrive" };
  }
  if (view.stage === "prepare") return { title: "Your journey", subtitle: route, content: <PrepareScreen view={view} /> };
  if (view.stage === "planb") {
    return { title: "Your journey", subtitle: "Hong Kong transfer · new plan", content: <PlanBScreen view={view} /> };
  }
  if (view.stage === "navigate" && !status.needs_manual_rebooking) {
    return {
      title: "Your journey", subtitle: `Hong Kong transfer · ${status.outbound.flight} to ${status.outbound.dest_city}`,
      content: <NavigateScreen view={view} onSwitch={actions.onSwitch} />,
    };
  }
  return {
    title: "Your journey", subtitle: `In flight · ${status.inbound.flight} to Hong Kong`,
    content: <ConnectScreen view={view} onChoose={actions.choose} onBags={actions.onBags} busy={actions.busy} />,
  };
}

