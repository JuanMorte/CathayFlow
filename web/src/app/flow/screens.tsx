// The passenger screens, one per Figma frame (S1 to S11). Every time comes from journey.ts (API times
// plus the offsets in sample.ts); every fixed detail comes from sample.ts.
import type { ReactNode } from "react";
import cathayLogo from "../../assets/flow/cathay-logo.png";
import checkinHall from "../../assets/flow/checkin-hall.jpg";
import heroBags from "../../assets/flow/hero-bags.jpg";
import heroHome from "../../assets/flow/hero-home.jpg";
import heroHk from "../../assets/flow/hero-hongkong.jpg";
import heroJakarta from "../../assets/flow/hero-jakarta.jpg";
import heroLondon from "../../assets/flow/hero-london.jpg";
import iconBell from "../../assets/flow/icon-bell.png";
import iconCar from "../../assets/flow/icon-car.png";
import iconCheckin from "../../assets/flow/icon-checkin.png";
import iconHome from "../../assets/flow/icon-home.png";
import iconOfficer from "../../assets/flow/icon-officer.png";
import iconPin from "../../assets/flow/icon-pin.png";
import iconPlane from "../../assets/flow/icon-plane.png";
import iconSofa from "../../assets/flow/icon-sofa.png";
import iconWalkerDark from "../../assets/flow/icon-walker-dark.png";
import iconWalker from "../../assets/flow/icon-walker.png";
import logoBolt from "../../assets/flow/logo-bolt.png";
import logoCitymapper from "../../assets/flow/logo-citymapper.png";
import logoGojek from "../../assets/flow/logo-gojek.png";
import logoGrab from "../../assets/flow/logo-grab.png";
import logoUber from "../../assets/flow/logo-uber.png";
import logoWaze from "../../assets/flow/logo-waze.png";
import mapBelt from "../../assets/flow/map-belt.jpg";
import mapCgk from "../../assets/flow/map-cgk.jpg";
import mapHkg from "../../assets/flow/map-hkg.jpg";
import miles from "../../assets/flow/mark-miles.png";
import shopBoost from "../../assets/flow/shop-boost.jpg";
import shopChagee from "../../assets/flow/shop-chagee.jpg";
import shopFore from "../../assets/flow/shop-fore.jpg";
import shopMcd from "../../assets/flow/shop-mcd.jpg";
import bagSolid from "../../assets/flow/svg/bag-solid.svg?raw";
import bagSvg from "../../assets/flow/svg/bag.svg?raw";
import carSvg from "../../assets/flow/svg/car.svg?raw";
import clockSvg from "../../assets/flow/svg/clock.svg?raw";
import exitSvg from "../../assets/flow/svg/exit.svg?raw";
import seatSvg from "../../assets/flow/svg/seat.svg?raw";
import { CABIN, HKG_DEPARTURE_TERMINAL, HKT, clock, dayMonth, fullDate, gmt, longDate, plusDays, sameDay, span, weekday, type Story } from "./journey";
import { SAMPLE } from "./sample";
import { AppLink, Card, Journey, NavGuide, Notice, PhotoHeader, Route, RouteCard, Section, Svg } from "./ui";

const MIN = 60000;
const ONE_STOP = "1 stop";
const mins = (ms: number) => Math.max(Math.round(ms / MIN), 0);
const plane = <img src={iconPlane} alt="" className="h-[18px] w-[18px] brightness-0" />;
const car = <img src={iconCar} alt="" className="h-[18px] w-[18px]" />;
const walker = <img src={iconWalkerDark} alt="" className="h-[18px] w-[18px]" />;
const svgIcon = (src: string) => `data:image/svg+xml;utf8,${encodeURIComponent(src)}`;

// ------------------------------------------------------------------ S1 Home

function FlowRow({ icon, title, detail, onClick }: { icon: ReactNode; title: string; detail: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="flex w-full items-center gap-[12px] rounded-[10px] border border-primary px-[12px] py-[11px] text-left">
      <span className="flex h-[32px] w-[32px] shrink-0 items-center justify-center rounded-full bg-primary text-white">{icon}</span>
      <span className="flex-1">
        <span className="block text-[15.5px] font-bold leading-tight text-black">{title}</span>
        <span className="mt-[3px] block font-sans text-[13px] text-black">{detail}</span>
      </span>
      <svg viewBox="0 0 10 17" className="h-[15px] w-[9px] text-black" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M1 1l7.5 7.5L1 16" /></svg>
    </button>
  );
}

export function FlowMark({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8" />
    </svg>
  );
}

export function flowLine(s: Story): string {
  const at = (ms: number) => clock(ms, s.originZone);
  switch (s.stage) {
    case "leave": return `Leave home at ${at(s.leaveHome)} ${sameDay(s.now, s.leaveHome, s.originZone) ? "today" : "tomorrow"}`;
    case "airport": return `Check in at the ${SAMPLE.checkinCounter.toLowerCase()}`;
    case "insideOrigin": return `Boarding at ${at(s.originBoarding)}, Gate ${SAMPLE.originGate}`;
    case "flying": return `Watching your connection to ${s.onward.flight}`;
    case "rebooked": return "Your connection has changed";
    case "insideHkg": return `Walk to ${s.onward.gate ? `Gate ${s.onward.gate}` : "your gate"} at ${clock(s.hkgWalkStart)}`;
    case "onward": return `On ${s.onward.flight} to ${s.destCity}`;
    default: return `Your bags arrive on Belt ${SAMPLE.belt}`;
  }
}

function bagLine(s: Story): string {
  if (s.now < s.checkIn) return "Your baggage hasn’t been dropped yet";
  if (!s.departed) return `${bagsWord(s)} checked in at ${s.origin}`;
  if (s.landed && s.now >= s.landed) return `Arriving on Belt ${SAMPLE.belt}`;
  return `${bagsWord(s)} ${s.status.bags === 1 ? "is" : "are"} on ${s.landedHkg ? s.onward.flight : s.status.inbound.flight}`;
}
const bagsWord = (s: Story) => (s.status.bags ?? 1) > 1 ? "Both bags" : "Your bag";

export function HomeScreen({ s, onFlow, onBags, onMenu, onBell }: {
  s: Story; onFlow: () => void; onBags: () => void; onMenu: () => void; onBell: () => void;
}) {
  const flights = `${s.status.inbound.flight}, ${s.onward.flight}`;
  const arrival = s.onward.arrival;
  const total = arrival ? mins(arrival - s.schedDep) : 0;
  return (
    <>
      <div className="relative h-[262px] w-full overflow-hidden">
        <img src={heroHome} alt="" className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-b from-black/10 to-black/30" />
        <img src={cathayLogo} alt="Cathay" className="absolute left-1/2 top-[106px] h-[40px] w-[40px] -translate-x-1/2" />
        <div className="absolute right-[38px] top-[109px] flex items-center gap-[22px] text-white">
          <button onClick={onBell} aria-label="Notifications" className="relative">
            <svg viewBox="0 0 24 24" className="h-[22px] w-[22px]" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M6 16V11a6 6 0 1 1 12 0v5l2 2H4zM10 20a2 2 0 0 0 4 0" /></svg>
            <span className="absolute right-0 top-0 h-[7px] w-[7px] rounded-full bg-[#E5322D]" />
          </button>
          <button onClick={onMenu} aria-label="More" className="text-[22px] leading-none">···</button>
        </div>
        <div className="absolute left-[15px] top-[160px] flex items-center gap-[20px] text-white">
          <span className="text-[24px] font-medium">Hello {s.name}</span>
          <span className="flex h-[17px] w-[26px] items-center justify-center rounded-[3px] bg-[#B89B5E]">
            <svg viewBox="0 0 10 10" className="h-[8px] w-[8px] text-white" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="M3 1l4 4-4 4" /></svg>
          </span>
        </div>
        <div className="absolute left-[14px] top-[209px] flex items-center gap-[10px] text-white">
          <img src={miles} alt="" className="h-[18px] w-[18px] brightness-0 invert" />
          <span className="text-[20px] font-bold">{SAMPLE.miles}</span>
          <span className="mx-[4px] h-[20px] w-px bg-white/80" />
          <span className="text-[15px]">Status Points</span>
          <span className="text-[20px] font-bold">{SAMPLE.statusPoints}</span>
        </div>
      </div>
      <div className="mx-[15px] mt-[23px] flex items-baseline justify-between">
        <h2 className="text-[22px] text-black">Your upcoming journey</h2>
        <button onClick={onFlow} className="text-[15px] text-primary">View all</button>
      </div>
      <Card className="mx-[15px] mt-[12px] px-[16px] pb-[12px] pt-[18px]">
        <div className="flex items-center text-[12.5px] font-light text-ink">
          <span>{longDate(s.schedDep, s.originZone)}</span><span className="mx-[9px] h-[14px] w-px bg-[#BDBDBD]" /><span>{flights}</span>
        </div>
        <div className="mt-[8px] flex items-baseline justify-between">
          <Route from={s.originCity} to={s.destCity} />
          <span className="text-[13px] font-light text-black">via Hong Kong</span>
        </div>
        <div className="mt-[16px] flex items-start justify-between">
          <span className="text-[15px] font-bold text-primary">{s.origin}</span>
          <span className="text-[12.5px] font-light text-black">{span(total)} · {ONE_STOP}</span>
          <span className="text-[15px] font-bold text-primary">{s.dest}</span>
        </div>
        <div className="relative flex items-center">
          <span className="w-[80px] text-[26px] text-black">{clock(s.schedDep, s.originZone)}</span>
          <div className="relative mx-1 h-[30px] flex-1">
            <div className="absolute left-[22px] right-0 top-1/2 h-px bg-[#D9D9D9]" />
            <span className="absolute left-0 top-1/2 -translate-y-1/2">{plane}</span>
            <span className="absolute left-1/2 top-1/2 h-[10px] w-[10px] -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-primary bg-white" />
            <span className="absolute left-1/2 top-[24px] -translate-x-1/2 text-[12px] font-bold text-primary">HKG</span>
            <span className="absolute right-0 top-1/2 h-[8px] w-[8px] -translate-y-1/2 rounded-full bg-[#D9D9D9]" />
          </div>
          <span className="relative w-[80px] text-right text-[26px] text-black">
            {arrival && <span className="absolute -left-[2px] -top-[2px] text-[11px] font-bold text-late">{plusDays(s.schedDep, s.originZone, arrival, s.destZone)}</span>}
            {arrival ? clock(arrival, s.destZone) : ""}
          </span>
        </div>
        <div className="flex justify-between text-[11px] font-light text-black">
          <span>{s.status.inbound.origin_terminal ?? ""}</span><span>{s.onward.terminal ?? ""}</span>
        </div>
        <div className="mt-[18px] flex flex-col gap-[10px]">
          <FlowRow icon={<FlowMark className="h-[18px] w-[18px]" />} title="Cathay Flow is on" detail={flowLine(s)} onClick={onFlow} />
          <FlowRow icon={<Svg src={bagSolid} className="h-[15px] w-[13px] text-white" />} title="Track your baggage" detail={bagLine(s)} onClick={onBags} />
        </div>
      </Card>
      <p className="mt-[10px] text-center font-sans text-[12px] text-muted">
        Last updated: {dayMonth(s.now, s.originZone)}, {clock(s.now, s.originZone)} ({gmt(s.now, s.originZone)})
      </p>
      <div className="mx-[15px] mt-[20px] flex items-center gap-[14px] rounded-[10px] border border-[#E2E2E2] bg-white px-[16px] py-[19px]">
        <svg viewBox="0 0 24 24" className="h-[20px] w-[20px] text-ink" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="M7 3h7l4 4v14H7zM14 3v4h4M10 12h5M10 16h5" /></svg>
        <span className="font-sans text-[13px] text-black">Check the <b className="text-primary">entry requirements</b> to enter {s.destCity}.</span>
      </div>
      <div className="mx-[15px] mb-[20px] mt-[21px] rounded-[10px] bg-[#E3EEEE] px-[18px] py-[14px]">
        <div className="text-[16px] font-bold text-black">Get Flow alerts</div>
        <div className="mt-[4px] font-sans text-[13px] text-black">Leave-home time, gate changes and bag updates, as they happen.</div>
        <div className="mt-[6px] text-[14px] font-bold text-primary">Turn on now</div>
      </div>
    </>
  );
}

// ------------------------------------------------------------------ S2 Settings

function Toggle({ on }: { on: boolean }) {
  return (
    <span className={`flex h-[28px] w-[46px] items-center rounded-full p-[3px] ${on ? "justify-end bg-primary" : "justify-start bg-[#CFCBC4]"}`}>
      <span className="h-[22px] w-[22px] rounded-full bg-white shadow" />
    </span>
  );
}

export function SettingsScreen({ s }: { s: Story }) {
  const bags = s.status.bags ?? 1;
  const prefs = [
    ["Walking pace", SAMPLE.prefs.pace], ["Lounge in Hong Kong", SAMPLE.prefs.lounge], ["Dietary needs", SAMPLE.prefs.diet],
    ["Checked bags", `${bags} ${bags === 1 ? "bag" : "bags"}`], ["Assistance", s.status.assistance_note ?? SAMPLE.prefs.assistance],
  ];
  const alerts = [
    ["Leave-home time", "When to leave, updated with live traffic"],
    ["Connection changes", "If a Cathay agent rebooks your flight"],
    ["Bag updates", "Each time your bags are scanned"],
  ];
  return (
    <div className="flex min-h-full flex-col bg-white">
      <div className="px-6 pt-[22px]">
        <h1 className="text-[32px] text-black">Settings</h1>
        <p className="mt-[4px] text-[14px] font-light text-black">
          For your trip to {s.destCity}, {weekday(s.schedDep, s.originZone)} {dayMonth(s.schedDep, s.originZone)}
        </p>
      </div>
      <div className="mx-4 mt-[16px] flex gap-[12px] rounded-[10px] bg-warn px-[12px] py-[12px]">
        <img src={iconBell} alt="" className="mt-[2px] h-[18px] w-[18px]" />
        <div>
          <div className="text-[16px] font-bold text-black">We value your privacy</div>
          <div className="text-[13px] font-light leading-snug text-black">Flow uses the checkpoints you pass, like check-in and boarding. No location tracking.</div>
          <div className="mt-[4px] text-[13px] font-bold text-primary">How Flow uses your data</div>
        </div>
      </div>
      <div className="px-6">
        <div className="mt-[28px] border-b border-[#E2E2E2] pb-[12px] text-[15px] text-[#8A6D1F]">Your preferences</div>
        {prefs.map(([title, value]) => (
          <div key={title} className="flex items-center justify-between border-b border-[#E2E2E2] py-[14px]">
            <div><div className="text-[17px] text-black">{title}</div><div className="mt-[4px] text-[13px] font-light text-black">{value}</div></div>
            <svg viewBox="0 0 10 17" className="h-[15px] w-[9px] text-black" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M1 1l7.5 7.5L1 16" /></svg>
          </div>
        ))}
        <div className="mt-[18px] border-b border-[#E2E2E2] pb-[12px] text-[15px] text-[#8A6D1F]">Alerts</div>
        {alerts.map(([title, detail]) => (
          <div key={title} className="flex items-center justify-between border-b border-[#E2E2E2] py-[14px] last:mb-[40px]">
            <div><div className="text-[17px] text-black">{title}</div><div className="mt-[4px] text-[13px] font-light text-black">{detail}</div></div>
            <Toggle on />
          </div>
        ))}
      </div>
      <div className="mt-auto bg-[#F1F0EC] px-6 py-[22px] text-[13px] font-light leading-relaxed text-muted">
        You can change these any time in Settings.<br />Turning Flow off deletes your preferences.
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ S2 Leave, S3 Airport

function departureRows(s: Story) {
  const at = (ms: number) => clock(ms, s.originZone);
  return [
    { icon: iconHome, title: "Leave home", detail: `${SAMPLE.homeArea} to ${s.origin} ${shortTerminal(s)}, ${SAMPLE.driveMin} min`, time: at(s.leaveHome) },
    { icon: iconCheckin, title: "Check in", detail: `${SAMPLE.checkinCounter}, est. ${SAMPLE.checkinMin} min`, time: at(s.checkIn) },
    { icon: iconOfficer, title: "Immigration and security", detail: `About ${SAMPLE.securityMin} min at this hour`, time: at(s.security) },
  ];
}
const shortTerminal = (s: Story) => (s.status.inbound.origin_terminal ?? "").replace("Terminal ", "T");

export function LeaveScreen({ s }: { s: Story }) {
  const at = (ms: number) => clock(ms, s.originZone);
  return (
    <>
      <PhotoHeader photo={heroJakarta} label="Departure" title="Plan your journey ahead" />
      <RouteCard date={longDate(s.schedDep, s.originZone)} from="Home" to={s.origin} left="Home" right={s.origin}
        middle={`${SAMPLE.driveMin} min drive`} icon={car} leftTime={at(s.leaveHome)} rightTime={at(s.checkIn)}
        leftNote={`${SAMPLE.homeArea}, ${SAMPLE.homeCity}`} rightNote={s.status.inbound.origin_terminal} />
      <Section title="Your Journey" action="View all"><Journey rows={departureRows(s)} done={s.now >= s.leaveHome ? 1 : 0} /></Section>
      <Section title="Transportation options">
        <AppLink logo={logoGojek} app="Gojek" rest="for taxi" />
        <AppLink logo={logoGrab} app="Grab" rest="for taxi" />
        <AppLink logo={logoWaze} app="Waze" rest="for driving/public transport" />
      </Section>
    </>
  );
}

export function AirportScreen({ s }: { s: Story }) {
  const at = (ms: number) => clock(ms, s.originZone);
  return (
    <>
      <PhotoHeader photo={heroJakarta} label="Departure" title={`Welcome to ${s.origin}`} />
      <RouteCard date={longDate(s.schedDep, s.originZone)} from="Check In" to="Immigration & Security" left="" right=""
        middle={`${SAMPLE.checkinToSecurityWalkMin} min walk`} icon={walker} leftTime={at(s.checkIn)} rightTime={at(s.security)}
        leftNote="Check In Counter" rightNote="Immigration & Security" />
      <Section title="Your Journey" action="View all"><Journey rows={departureRows(s)} done={1} /></Section>
      <Section title="Navigation guide">
        <NavGuide title={`Head straight to Gate ${SAMPLE.originTerminalGateRange}`} detail={`${SAMPLE.airportNavMin} mins`} image={checkinHall}
          footer={(
            <div className="flex items-center gap-[12px] px-[14px] py-[12px]">
              <img src={iconCheckin} alt="" className="h-[22px] w-[22px]" />
              <span className="font-sans text-[12px] text-black">Have your passport ready for verification</span>
            </div>
          )} />
      </Section>
    </>
  );
}

// ------------------------------------------------------------------ S4 Inside the airport (origin and Hong Kong)

function Shop({ photo, name, near }: { photo: string; name: string; near: string }) {
  return (
    <Card className="w-[177px] shrink-0 overflow-hidden">
      <img src={photo} alt="" className="h-[118px] w-full object-cover" />
      <div className="px-[11px] pb-[12px] pt-[10px]">
        <div className="text-[11px] font-light text-black">Food &amp; Beverage</div>
        <div className="text-[16px] text-black">{name}</div>
        <div className="mt-[8px] flex items-center gap-[3px] text-[9px] font-light text-black">
          <img src={iconPin} alt="" className="h-[12px] w-[12px]" />{near}
        </div>
      </div>
    </Card>
  );
}

export function InsideScreen({ s, place }: { s: Story; place: "origin" | "hkg" }) {
  const hkg = place === "hkg";
  const zone = hkg ? HKT : s.originZone;
  const at = (ms: number) => clock(ms, zone);
  const gate = hkg ? s.onward.gate : SAMPLE.originGate;
  const gateName = gate ? `Gate ${gate}` : "your gate";
  const walk = hkg ? s.hkgWalkMin : SAMPLE.originWalkMin;
  const boarding = hkg ? s.hkgBoarding : s.originBoarding;
  const walkStart = hkg ? s.hkgWalkStart : s.originWalkStart;
  const relax = mins(walkStart - s.now);
  const shops = hkg
    ? [{ photo: shopChagee, name: "Chagee", near: "Near Gate 30, Departures Level (L6)" }, { photo: shopMcd, name: "McDonald’s", near: "Near Gate 11, Departures Level (L6)" }]
    : [{ photo: shopFore, name: "Fore Coffee", near: "Near Gate 6, Terminal 3" }, { photo: shopBoost, name: "Boost Juice", near: "Near Gate 8, Terminal 3" }];
  return (
    <>
      <PhotoHeader photo={hkg ? heroHk : heroJakarta} label="Inside the airport" title={`Welcome to ${hkg ? "HKIA" : s.origin}`} />
      <RouteCard date={longDate(s.now, zone)} from="Your Location" to={gate ? gateName : "Your gate"} left="" right=""
        middle={`${walk} min walk`} icon={walker} midTime={at(s.now + walk * MIN)} leftTime={at(s.now)} rightTime={at(boarding)}
        leftNote="Your Location" rightNote="Boarding Time" />
      <Section title="Your Journey" action="View all">
        <Journey rows={[
          { icon: iconSofa, title: "Explore the Terminal", detail: relax > 0 ? `${span(relax)} to relax` : "Time to head to your gate", time: at(s.now) },
          { icon: iconWalker, title: `Walk to ${gateName}`, detail: `About ${walk} min at your pace`, time: at(Math.max(walkStart, s.now)) },
        ]} />
      </Section>
      <Section title="Navigation guide">
        <NavGuide title={hkg ? "Continue straight past Chanel" : "Continue straight past Periplus"}
          detail={`Turn right at the next junction${hkg ? "," : " ·"} ${SAMPLE.airportNavMin} min`}
          image={hkg ? mapHkg : mapCgk} />
      </Section>
      <Section title="Explore the Terminal">
        <div className="no-scrollbar -mx-[8px] flex gap-[8px] overflow-x-auto px-[8px] pb-[10px]">
          {shops.map((shop) => <Shop key={shop.name} {...shop} />)}
        </div>
      </Section>
    </>
  );
}

// ------------------------------------------------------------------ S6 Connection (rebooked, or watched while flying)

function onwardCard(s: Story) {
  const dep = s.onward.dep;
  const arr = s.onward.arrival;
  const plus = arr ? plusDays(dep, HKT, arr, s.destZone) : "";
  const terminal = s.onward.terminal ?? "";
  return (
    <RouteCard date={longDate(dep)} extra={s.onward.flight} from="HKG" to={s.dest} left="HKG" right={s.dest}
      middle={arr ? span(mins(arr - dep)) : undefined} icon={plane} leftTime={clock(dep)} rightTime={arr ? clock(arr, s.destZone) : ""}
      plus={plus} leftNote={HKG_DEPARTURE_TERMINAL} rightNote={plus && arr ? `${terminal}, ${weekday(arr, s.destZone)}` : terminal} />
  );
}

function SortedRow({ icon, title, detail, last }: { icon: string; title: string; detail: string; last?: boolean }) {
  return (
    <div className={`flex items-center gap-[16px] py-[16px] ${last ? "" : "border-b border-[#E2E2E2]"}`}>
      <span className="flex h-[36px] w-[36px] shrink-0 items-center justify-center rounded-full bg-[#F1F1F1] text-primary">
        <Svg src={icon} className="h-[13px] w-[13px]" />
      </span>
      <div>
        <div className="text-[15.5px] font-bold text-black">{title}</div>
        <div className="font-sans text-[12px] text-muted">{detail}</div>
      </div>
    </div>
  );
}

export function RebookedScreen({ s }: { s: Story }) {
  const together = s.status.companions.length > 0;
  const bags = s.status.bags ?? 1;
  return (
    <>
      <PhotoHeader photo={heroHk} label="Connecting" title="Your connection has been rebooked" />
      {onwardCard(s)}
      <Notice icon={iconBell} title={`Rebooked by a Cathay agent at ${s.rebookedAt ? clock(s.rebookedAt) : ""}`}>
        In case of any issues, please contact Cathay Pacific hotline at <span className="font-normal">{SAMPLE.hotline}</span>
      </Notice>
      <Section title="What we sorted for you">
        <Card className="px-[16px] py-[2px]">
          <SortedRow icon={clockSvg} title={`Flight rebooked on ${s.onward.flight}`}
            detail={`Arrive at ${s.onward.gate ? `Gate ${s.onward.gate}` : "your gate"} by ${clock(s.atGateBy)}`} />
          <SortedRow icon={seatSvg} title={`Seats reassigned to ${s.onward.seat ?? "a new seat"}`}
            detail={together ? "Seats rebooked together" : `${CABIN[s.status.cabin]} seat on ${s.onward.flight}`} />
          <SortedRow icon={bagSvg} title="Bags moved" detail={`${bags} ${bags === 1 ? "bag" : "bags"} will arrive with ${s.onward.flight}`} last />
        </Card>
      </Section>
    </>
  );
}

export function FlyingScreen({ s }: { s: Story }) {
  const hold = s.status.backup_hold;
  return (
    <>
      <PhotoHeader photo={heroHk} label="Connecting" title="Your connection in Hong Kong" />
      {onwardCard(s)}
      {hold && (
        <Notice icon={iconBell} title={`A seat on ${hold.flight} is held for you`}>
          Just in case {s.status.inbound.flight} lands too late. A Cathay agent will let you know if anything changes.
        </Notice>
      )}
      <Section title="Your Journey">
        <Journey rows={[
          { icon: iconPlane, title: "Land in Hong Kong", detail: `${s.status.inbound.flight} from ${s.originCity}`, time: clock(s.inboundAt) },
          { icon: iconWalker, title: `Walk to ${s.onward.gate ? `Gate ${s.onward.gate}` : "your gate"}`, detail: `About ${s.hkgWalkMin} min at your pace`, time: clock(s.inboundAt + SAMPLE.walkBufferMin * MIN) },
          { icon: iconSofa, title: "Boarding starts", detail: `${s.onward.flight} departs at ${clock(s.onward.dep)}`, time: clock(s.hkgBoarding) },
        ]} />
      </Section>
    </>
  );
}

// ------------------------------------------------------------------ S10 Bags

export function BagsScreen({ s }: { s: Story }) {
  const arrived = Boolean(s.landed && s.now >= s.landed);
  const departedHkg = s.now >= s.onward.dep;
  const loaded = s.onward.dep - SAMPLE.onwardBagsLoadedBeforeMin * MIN;
  const count = s.status.bags ?? 1;
  const tags = SAMPLE.bagTags.slice(0, count);
  const bag = <Svg src={bagSolid} className="h-[14px] w-[12px] text-black" />;
  return (
    <>
      <PhotoHeader photo={heroBags} label="Your bags" title={<span>Hong Kong <span className="font-normal">to</span> {s.destCity}</span>} />
      <RouteCard date={longDate(s.onward.dep)} extra={`${count} ${count === 1 ? "bag" : "bags"}`} from="Hong Kong" to={s.destCity}
        left="HKG" right={s.dest} middle={`On ${s.onward.flight}`} icon={bag} line={arrived ? "end" : "start"}
        leftTime={clock(loaded)} rightTime={s.belt ? clock(s.belt, s.destZone) : ""} leftNote="Loaded"
        rightNote={arrived ? `Belt ${SAMPLE.belt}` : s.onward.terminal} />
      <Section title="Bag Journey">
        {tags.map((tag, index) => {
          const first = index === 0;
          const line = arrived
            ? (first ? `Arrived on Belt ${SAMPLE.belt}` : `Unloading to Belt ${SAMPLE.belt}`)
            : (first || departedHkg ? `Loaded to ${s.onward.flight}` : `On cargo to be loaded to ${s.onward.flight}`);
          const tagText = arrived ? (first ? `belt ${SAMPLE.belt}` : `max. ${SAMPLE.lastBagMaxMin} min`) : "on track";
          return (
            <Card key={tag} className="mb-[11px] flex items-center gap-[14px] px-[16px] py-[17px]">
              <span className="flex h-[36px] w-[36px] items-center justify-center rounded-full bg-[#F1F1F1]">{bag}</span>
              <div className="flex-1">
                <div className="text-[15.5px] font-bold text-black">Bag {index + 1} <span className="mx-[4px] font-light text-[#BDBDBD]">|</span> {tag}</div>
                <div className="font-sans text-[12.5px] text-muted">{line}</div>
              </div>
              <span className="text-[16px] text-primary">{tagText}</span>
            </Card>
          );
        })}
      </Section>
      {arrived && (
        <Section title="Baggage Progress">
          <Card className="overflow-hidden">
            <div className="flex items-center gap-[14px] px-[14px] py-[8px]">
              <Svg src={bagSolid} className="h-[28px] w-[24px] text-primary" />
              <div>
                <div className="font-sans text-[13px] font-bold text-black">{SAMPLE.unloadedPercent}% baggage unloaded</div>
                <div className="font-sans text-[10.5px] text-muted">estimated {SAMPLE.beltEtaMin} mins to arrive at Belt {SAMPLE.belt}</div>
              </div>
            </div>
            <img src={mapBelt} alt="" className="block h-[210px] w-full object-cover" />
          </Card>
        </Section>
      )}
    </>
  );
}

// ------------------------------------------------------------------ S11 Arrive

export function ArriveScreen({ s, exit }: { s: Story; exit: boolean }) {
  const at = (ms: number | null) => (ms ? clock(ms, s.destZone) : "");
  const rows = exit
    ? [{ icon: svgIcon(exitSvg), title: "Customs and exit", detail: `About ${SAMPLE.customsMin} min`, time: at(s.exit) },
       { icon: svgIcon(carSvg), title: "Taxi to your hotel", detail: "No traffic signals", time: at(s.taxi) }]
    : [{ icon: iconPlane, title: `Landed in ${s.destCity}`, detail: `${s.onward.flight} at ${s.onward.terminal ?? ""}`, time: at(s.landed) },
       { icon: iconOfficer, title: "UK Border", detail: `About ${SAMPLE.borderMin} min right now`, time: at(s.border) },
       { icon: svgIcon(bagSolid.replace('fill="black"', 'fill="#367877"')), title: `Belt ${SAMPLE.belt}`, detail: "Priority bags come out first", time: at(s.belt) }];
  return (
    <>
      <PhotoHeader photo={heroLondon} label="Arrival" title={`Welcome to ${s.dest}`} />
      <RouteCard date={s.landed ? longDate(s.landed, s.destZone) : ""} from={s.dest} to={SAMPLE.hotel} left={s.dest} right="Hotel"
        middle={`${SAMPLE.hotelDriveMin} min drive`} icon={car} leftTime={at(s.exit)} rightTime={at(s.hotel)}
        leftNote={s.onward.terminal} rightNote="From your itinerary" />
      <Section title="Your Journey"><Journey rows={rows} /></Section>
      {exit && (
        <Section title="Transportation options">
          <AppLink logo={logoUber} app="Uber" rest="for taxi" wide />
          <AppLink logo={logoBolt} app="Bolt" rest="for taxi" wide />
          <AppLink logo={logoCitymapper} app="CityMapper" rest="for public transport" />
        </Section>
      )}
    </>
  );
}

// ------------------------------------------------------------------ S5 Lock screen

export function LockScreen({ s, title, body, onOpen, onClose }: {
  s: Story; title: string; body: string; onOpen: () => void; onClose: () => void;
}) {
  const inFlight = s.departed && !s.landedHkg;
  const hoursAgo = Math.max(Math.round((s.now - s.originBagsLoaded) / 3600000), 0);
  return (
    <div className="absolute inset-0 z-40 flex flex-col bg-gradient-to-b from-[#2E5F68] via-[#4B7F86] to-[#5E8E92] font-sans text-white" onClick={onClose}>
      <div className="flex items-center justify-between px-[22px] pt-[16px] text-[15px] font-semibold"><span>Cathay Wi-Fi</span></div>
      <svg viewBox="0 0 24 24" className="mx-auto mt-[12px] h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M7 11V8a5 5 0 0 1 10 0v3M6 11h12v9H6z" /></svg>
      <div className="mt-[18px] text-center text-[20px] font-semibold">{fullDate(s.now)}</div>
      <div className="text-center text-[96px] font-semibold leading-none tracking-tight">{clock(s.now)}</div>
      {inFlight && <div className="mt-[6px] text-center text-[14px]">In flight · {s.status.inbound.flight} to Hong Kong</div>}
      <div className="mt-auto px-[10px] pb-[110px]">
        <button onClick={(e) => { e.stopPropagation(); onOpen(); }}
          className="flex w-full gap-[12px] rounded-[22px] bg-white/85 px-[14px] py-[14px] text-left text-black backdrop-blur">
          <span className="flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-[9px] bg-primary text-white"><FlowMark className="h-[20px] w-[20px]" /></span>
          <span className="flex-1">
            <span className="flex justify-between text-[13px] text-black/60"><span className="font-semibold tracking-wide">CATHAY</span><span>now</span></span>
            <span className="block text-[15px] font-semibold">{title}</span>
            <span className="block text-[15px] leading-snug">{body}</span>
          </span>
        </button>
        {s.departed && (
          <div className="mt-[10px] flex gap-[12px] rounded-[22px] bg-white/85 px-[14px] py-[14px] text-black backdrop-blur">
            <span className="flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-[9px] bg-primary text-white"><Svg src={bagSolid} className="h-[16px] w-[14px]" /></span>
            <span className="flex-1">
              <span className="flex justify-between"><span className="text-[15px] font-semibold">{bagsWord(s)} {s.status.bags === 1 ? "is" : "are"} on {s.status.inbound.flight}</span>
                <span className="text-[13px] text-black/60">{hoursAgo}h ago</span></span>
              <span className="block text-[14px]">Loaded at {clock(s.originBagsLoaded, s.originZone)} in {s.originCity}</span>
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
