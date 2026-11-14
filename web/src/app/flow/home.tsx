// Cathay app home with the Flow entry (s1-home.png), the lock-screen alert (s4-lockscreen.png) and
// Set up Cathay Flow (s2-setup.png).
import { useState } from "react";
import { Brushwing, Card, HeroCard, Icon, PrimaryButton, StatusBar } from "./kit";
import { clock, fullDate, longDate, shortDate, span, type View } from "./journey";

function CityLights() {
  // A night skyline glow in CSS (no photo asset in the repo).
  return (
    <div className="pointer-events-none absolute inset-0"
      style={{
        backgroundImage: [
          "radial-gradient(ellipse 60% 35% at 70% 92%, rgba(255,190,110,.55), transparent 70%)",
          "radial-gradient(ellipse 45% 25% at 20% 96%, rgba(255,170,90,.45), transparent 70%)",
          "radial-gradient(circle at 37% 61%, rgba(255,214,150,.75) 0 .8px, transparent 1.3px)",
          "radial-gradient(circle at 71% 43%, rgba(255,226,170,.6) 0 .7px, transparent 1.2px)",
          "radial-gradient(circle at 18% 77%, rgba(255,200,130,.7) 0 .9px, transparent 1.4px)",
          "linear-gradient(180deg, #0B1A2B 0%, #10263A 40%, #1F3647 70%, #4A4B4C 100%)",
        ].join(","),
        backgroundSize: "100% 100%, 100% 100%, 37px 23px, 53px 29px, 29px 41px, 100% 100%",
        backgroundPosition: "0 0, 0 0, 0 120px, 11px 135px, 5px 150px, 0 0",
        backgroundRepeat: "no-repeat, no-repeat, repeat-x, repeat-x, repeat-x, no-repeat",
      }} />
  );
}

export function HomeScreen({ view, onOpenFlow, onMenu }: { view: View; onOpenFlow: () => void; onMenu: () => void }) {
  const { trip, status, sample, flight, originDeparture, originZone, destZone, origin, dest } = view;
  const [alertsCard, setAlertsCard] = useState(true);
  const first = trip.passenger.name.split(" ")[0];
  const total = flight.arrival ? (flight.arrival - originDeparture) / 60000 : null;
  const entry = view.now < view.leaveHome
    ? `Leave home at ${clock(view.leaveHome, originZone)}`
    : view.rebooked ? `You're on ${flight.no} now`
      : status.zone === "SAFE" ? "Watching your Hong Kong connection" : "Your Hong Kong connection is tight";
  return (
    <div className="flex flex-col pb-3">
      <div className="relative h-[230px] overflow-hidden rounded-b-[26px] text-white">
        <CityLights />
        <div className="relative"><StatusBar time={clock(view.now)} dark /></div>
        <div className="relative flex items-center justify-between px-4 pt-3 sm:pt-0">
          <span className="w-[52px]" />
          <Brushwing className="h-[30px] w-[42px] text-white" />
          <span className="flex items-center gap-3">
            <span className="relative">
              <Icon name="bell" className="h-[24px] w-[24px]" />
              <span className="absolute right-[1px] top-[1px] h-[8px] w-[8px] rounded-full bg-saffron" />
            </span>
            <button onClick={onMenu} aria-label="More"><Icon name="more" className="h-[24px] w-[24px]" /></button>
          </span>
        </div>
        <div className="relative mt-7 flex items-center gap-3 px-4">
          <h1 className="text-[25px] font-medium">Hello {first}</h1>
          <span className="flex h-[20px] w-[30px] items-center justify-end rounded-[3px] bg-gradient-to-br from-[#C9A55B] to-[#8A6A2B] pr-[3px]">
            <Icon name="chevron" className="h-[12px] w-[12px] text-white" />
          </span>
        </div>
        <p className="relative mt-3 flex items-center gap-2 px-4 text-[17px]">
          <span className="text-[19px] font-light italic">A</span><b>{sample.asiaMiles.toLocaleString("en-GB")}</b>
          <span className="mx-1 h-[18px] w-px bg-white/70" />
          Status Points <b>{sample.statusPoints}</b>
        </p>
      </div>

      <div className="mx-4 mt-5 flex items-baseline justify-between">
        <h2 className="text-[21px] text-ink">Your upcoming journey</h2>
        <span className="text-[15px] text-primary">View all</span>
      </div>

      <Card className="mx-4 mt-3 px-4 pb-3 pt-[14px] shadow-[0_2px_10px_rgba(0,0,0,.06)]">
        <div className="flex items-center gap-[10px] text-[13.5px] text-ink">
          <span>{longDate(originDeparture, originZone)}</span>
          <span className="h-[14px] w-px bg-[#CFCBC4]" />
          <span>{status.inbound.flight} · {status.outbound.flight}</span>
        </div>
        <div className="mt-2 flex items-baseline justify-between">
          <p className="text-[18px] font-bold text-deep">
            {status.inbound.origin_city} <span className="font-normal text-ink">to</span> {status.outbound.dest_city}
          </p>
          <span className="text-[13px] text-muted">via Hong Kong</span>
        </div>
        <div className="mt-3 flex items-end">
          <div>
            <div className="text-[15px] font-bold text-deep">{origin}</div>
            <div className="text-[29px] leading-tight text-ink">{clock(originDeparture, originZone)}</div>
            <div className="text-[12px] text-ink">{sample.originTerminal}</div>
          </div>
          <div className="relative mx-2 mb-[30px] flex flex-1 items-center text-ink">
            {total && (
              <span className="absolute -top-[19px] left-1/2 -translate-x-1/2 whitespace-nowrap text-[12px] text-ink">
                {span(total)} · one stop
              </span>
            )}
            <Icon name="plane" className="h-[18px] w-[18px] shrink-0 rotate-90" />
            <span className="h-px flex-1 bg-[#B9B5AE]" />
            <span className="relative flex flex-col items-center">
              <span className="h-[11px] w-[11px] rounded-full border-2 border-deep bg-white" />
              <span className="absolute top-[13px] text-[10.5px] font-bold text-deep">HKG</span>
            </span>
            <span className="h-px flex-1 bg-[#B9B5AE]" />
            <span className="h-[7px] w-[7px] rounded-full bg-[#B9B5AE]" />
          </div>
          <div className="text-right">
            <div className="text-[15px] font-bold text-deep">{dest}</div>
            <div className="text-[29px] leading-tight text-ink">{flight.arrival ? clock(flight.arrival, destZone) : ""}</div>
            <div className="text-[12px] text-ink">{sample.destinationTerminal}</div>
          </div>
        </div>
        <button onClick={onOpenFlow}
          className="mt-4 flex w-full items-center gap-3 rounded-[10px] bg-info px-3 py-[10px] text-left focus-visible:ring-2 focus-visible:ring-primary">
          <span className="flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-full bg-deep text-white">
            <Icon name="flow" className="h-[20px] w-[20px]" />
          </span>
          <span className="flex-1">
            <span className="block text-[15px] font-bold text-deep">Cathay Flow is on</span>
            <span className="block text-[13.5px] text-ink">{entry}</span>
          </span>
          <Icon name="chevron" className="h-5 w-5 text-deep" />
        </button>
      </Card>
      <p className="mt-2 text-center text-[12.5px] text-muted">Last updated: {shortDate(view.now)}, {clock(view.now)} (HKT)</p>

      <Card className="mx-4 mt-4 flex items-center gap-3 px-4 py-4">
        <Icon name="doc" className="h-6 w-6 text-ink" />
        <span className="text-[13.5px] text-ink">
          Check the <b className="text-primary">entry requirements</b> to enter {status.outbound.dest_city}.
        </span>
      </Card>

      {alertsCard && (
        <div className="relative mx-4 mt-4 flex gap-3 rounded-[12px] bg-info px-4 py-4">
          <span className="flex h-[44px] w-[44px] shrink-0 items-center justify-center rounded-full bg-white text-deep">
            <Icon name="bell" className="h-[22px] w-[22px]" />
          </span>
          <div className="flex-1 pr-5">
            <div className="text-[16px] font-bold text-ink">Get Flow alerts</div>
            <div className="text-[13.5px] text-ink">Leave-home time, gate changes and bag updates, as they happen.</div>
            <div className="mt-1 text-[14px] font-bold text-primary">Turn on now</div>
          </div>
          <button onClick={() => setAlertsCard(false)} aria-label="Close" className="absolute right-3 top-3 text-ink">
            <Icon name="close" className="h-5 w-5" />
          </button>
        </div>
      )}
    </div>
  );
}

export type Alert = { title: string; body: string };

export function LockAlert({ view, alert, onOpen, onClose }: { view: View; alert: Alert; onOpen: () => void; onClose: () => void }) {
  const { status, originDeparture, originZone, origin, sample, now } = view;
  const flying = !["Landed", "At gate"].includes(status.inbound.status) && now >= originDeparture;
  const loaded = originDeparture - 40 * 60000;
  const ago = Math.max(Math.round((now - loaded) / 3600000), 0);
  return (
    <div className="absolute inset-0 z-40 flex flex-col overflow-hidden text-white" onClick={onClose}
      style={{ background: "linear-gradient(170deg,#2D5D62 0%,#3E6E72 45%,#4B7B7E 60%,#2E5A5D 100%)" }}>
      <div className="pointer-events-none absolute -bottom-24 -left-10 h-[260px] w-[520px] rounded-[50%] border-[30px] border-white/5" />
      <StatusBar time="" carrier="Cathay Wi-Fi" dark />
      <div className="mt-4 flex flex-col items-center sm:mt-2">
        <Icon name="lock" className="h-[18px] w-[18px]" />
        <p className="mt-3 text-[19px] font-bold">{fullDate(now)}</p>
        <p className="text-[84px] font-bold leading-[1.05] tracking-tight">{clock(now)}</p>
        <p className="mt-1 text-[13.5px]">{flying ? `In flight · ${status.inbound.flight} to Hong Kong` : "Hong Kong"}</p>
      </div>
      <div className="mt-auto px-3 pb-6" onClick={(e) => e.stopPropagation()}>
        <button onClick={onOpen}
          className="w-full rounded-[22px] bg-white/[0.88] px-4 pb-4 pt-3 text-left text-ink shadow-xl backdrop-blur focus-visible:ring-2 focus-visible:ring-white">
          <div className="flex items-center gap-2 text-[12px] text-muted">
            <span className="flex h-[30px] w-[30px] items-center justify-center rounded-[8px] bg-deep text-white">
              <Icon name="flow" className="h-[17px] w-[17px]" />
            </span>
            <span className="flex-1 font-bold tracking-wide">CATHAY</span>
            <span>now</span>
          </div>
          <p className="mt-2 text-[15px] font-bold">{alert.title}</p>
          <p className="text-[14px] leading-snug">{alert.body} Tap to see your plan.</p>
        </button>
        <div className="mx-4 h-[10px] rounded-b-[16px] bg-white/45" />
        <div className="mt-3 flex items-center gap-3 rounded-[20px] bg-white/[0.72] px-4 py-3 text-ink">
          <span className="flex h-[30px] w-[30px] items-center justify-center rounded-[8px] bg-deep text-white">
            <Icon name="bag" className="h-[17px] w-[17px]" />
          </span>
          <span className="flex-1">
            <span className="block text-[14px] font-bold">
              {sample.bags.length === 1 ? "Your bag is" : "Both bags are"} on {status.inbound.flight}
            </span>
            <span className="block text-[13px]">Loaded at {clock(loaded, originZone)} in {status.inbound.origin_city || origin}</span>
          </span>
          <span className="self-start text-[12px] text-muted">{ago ? `${ago}h ago` : "now"}</span>
        </div>
        <div className="mt-10 flex justify-between px-6">
          <span className="flex h-[50px] w-[50px] items-center justify-center rounded-full bg-black/25"><Icon name="flow" className="h-6 w-6" /></span>
          <span className="flex h-[50px] w-[50px] items-center justify-center rounded-full bg-black/25"><Icon name="camera" className="h-6 w-6" /></span>
        </div>
        <div className="mt-4 flex justify-center"><span className="h-[5px] w-[134px] rounded-full bg-white" /></div>
      </div>
    </div>
  );
}

export function SetupScreen({ view, onDone }: { view: View; onDone: () => void }) {
  const { trip, sample, status, originDeparture, originZone } = view;
  const [alerts, setAlerts] = useState(true);
  const rows = [
    { icon: "people", title: "Travelling with", detail: trip.passenger.group_size > 1 ? `${trip.passenger.group_size} people` : "Just you" },
    { icon: "walk", title: "Walking pace", detail: "Relaxed · learned from your recent trips" },
    { icon: "cup", title: "Lounge in Hong Kong", detail: `${sample.lounge} · your usual` },
    { icon: "bag", title: "Checked bags", detail: `${sample.bags.length === 1 ? "One bag" : `${sample.bags.length} bags`} · from your booking` },
  ];
  return (
    <div className="flex flex-col gap-3 pb-4">
      <HeroCard tag="Your journey, handled">
        <p className="text-[16px] leading-snug">Flow will handle your flight experience until you reach your designated location.</p>
        <p className="mt-4 text-[13px] text-white/90">Tell us a little about this trip.</p>
      </HeroCard>
      <div className="mx-4 flex flex-col gap-3">
        <Card className="px-4">
          {rows.map((row, i) => (
            <div key={row.title} className={`flex items-center gap-3 py-[14px] ${i < rows.length - 1 ? "border-b border-line" : ""}`}>
              <span className="flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-full bg-info text-deep">
                <Icon name={row.icon} className="h-5 w-5" />
              </span>
              <div className="flex-1">
                <div className="text-[15px] font-bold text-ink">{row.title}</div>
                <div className="text-[13px] text-muted">{row.detail}</div>
              </div>
              <Icon name="chevron" className="h-5 w-5 text-ink" />
            </div>
          ))}
        </Card>
        <Card className="flex items-center gap-3 px-4 py-[14px]">
          <span className="flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-full bg-info text-deep">
            <Icon name="bell" className="h-5 w-5" />
          </span>
          <div className="flex-1">
            <div className="text-[15px] font-bold text-ink">Alerts</div>
            <div className="text-[13px] text-muted">Leave-home time, gates, bags</div>
          </div>
          <button role="switch" aria-checked={alerts} onClick={() => setAlerts(!alerts)}
            className={`flex h-[30px] w-[50px] items-center rounded-full p-[3px] transition ${alerts ? "justify-end bg-primary" : "justify-start bg-[#CFCBC4]"}`}>
            <span className="h-[24px] w-[24px] rounded-full bg-white shadow" />
          </button>
        </Card>
        <div className="flex gap-3 rounded-[12px] bg-warn px-4 py-4 text-warn-text">
          <Icon name="lock" className="mt-[2px] h-5 w-5 shrink-0" />
          <div>
            <div className="text-[15px] font-bold text-ink">Checkpoints, not tracking</div>
            <div className="text-[13px] text-ink/80">Flow uses the checkpoints you pass (check-in, lounge, boarding). It never tracks your location.</div>
          </div>
        </div>
        <div className="flex pt-6"><PrimaryButton onClick={onDone}>Turn on Flow for this trip</PrimaryButton></div>
        <p className="text-center text-[11px] text-muted">{status.inbound.origin_city} → {status.outbound.dest_city} · {shortDate(originDeparture, originZone)}</p>
      </div>
    </div>
  );
}
