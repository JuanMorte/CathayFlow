// Time helpers and the passenger's story at the replay time: which stage they are in, and every
// time shown on the screens. Flight times come from the API; offsets come from sample.ts.
import type { ConnectionStatus, Trip } from "../../api/client";
import { SAMPLE } from "./sample";

const HKT = "Asia/Hong_Kong";
const ZONES: Record<string, string> = {
  LHR: "Europe/London", MAN: "Europe/London", CDG: "Europe/Paris", AMS: "Europe/Amsterdam", FRA: "Europe/Berlin",
  JFK: "America/New_York", LAX: "America/Los_Angeles", SFO: "America/Los_Angeles", YVR: "America/Vancouver",
  YYZ: "America/Toronto", SYD: "Australia/Sydney", MEL: "Australia/Melbourne", BNE: "Australia/Brisbane",
  SIN: "Asia/Singapore", BKK: "Asia/Bangkok", CGK: "Asia/Jakarta", TPE: "Asia/Taipei", NRT: "Asia/Tokyo",
  HND: "Asia/Tokyo", ICN: "Asia/Seoul",
};
export const zoneOf = (airport: string) => ZONES[airport] ?? HKT;
export { HKT };

const HAS_OFFSET = /([+-]\d{2}:\d{2}|Z)$/;

/** A time with an offset → ms; a local time without one is read in `zone`. */
export function instant(iso: string, zone = HKT): number {
  if (HAS_OFFSET.test(iso)) return new Date(iso).getTime();
  const guess = Date.parse(`${iso.length === 16 ? `${iso}:00` : iso}Z`);
  return guess - offsetMs(guess, zone);
}

function offsetMs(at: number, zone: string): number {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-GB", {
    timeZone: zone, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  }).formatToParts(at).map((p) => [p.type, p.value]));
  return Date.UTC(+parts.year, +parts.month - 1, +parts.day, +parts.hour, +parts.minute, +parts.second) - at;
}

export const clock = (ms: number, zone = HKT) =>
  new Date(ms).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: zone });

/** "Tue 15 Dec 2026" */
export const longDate = (ms: number, zone = HKT) => {
  const d = new Date(ms);
  const part = (o: Intl.DateTimeFormatOptions) => d.toLocaleDateString("en-GB", { ...o, timeZone: zone });
  return `${part({ weekday: "short" })} ${part({ day: "numeric" })} ${part({ month: "short" })} ${part({ year: "numeric" })}`;
};
/** "14 Dec" */
export const dayMonth = (ms: number, zone = HKT) =>
  new Date(ms).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: zone });
export const weekday = (ms: number, zone = HKT) =>
  new Date(ms).toLocaleDateString("en-GB", { weekday: "short", timeZone: zone });
export const fullDate = (ms: number, zone = HKT) =>
  new Date(ms).toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", timeZone: zone }).replace(",", "");

function localDay(ms: number, zone: string): number {
  return Date.parse(`${new Date(ms + offsetMs(ms, zone)).toISOString().slice(0, 10)}T00:00:00Z`);
}
/** "+1" when `ms` falls on a later local calendar day than `from` does (each in its own zone). */
export function plusDays(from: number, fromZone: string, ms: number, zone: string): string {
  const days = Math.round((localDay(ms, zone) - localDay(from, fromZone)) / 86400000);
  return days > 0 ? `+${days}` : "";
}
export const sameDay = (a: number, b: number, zone: string) => localDay(a, zone) === localDay(b, zone);

/** "GMT +7" for a zone at a moment. */
export const gmt = (ms: number, zone: string) => {
  const hours = Math.round(offsetMs(ms, zone) / 3600000);
  return `GMT ${hours >= 0 ? "+" : "-"}${Math.abs(hours)}`;
};

export function span(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return h ? `${h}h ${m}m` : `${m} min`;
}
const MIN = 60000;

export type Stage = "leave" | "airport" | "insideOrigin" | "flying" | "rebooked" | "insideHkg" | "onward" | "arrive" | "exit";

export type Story = {
  trip: Trip;
  status: ConnectionStatus;
  now: number;
  name: string;               // "Ms Wijaya", or the first name when no title is known
  origin: string; originCity: string; originZone: string;
  dest: string; destCity: string; destZone: string;
  schedDep: number; departed: number | null;
  leaveHome: number; checkIn: number; security: number; originBoarding: number; originWalkStart: number;
  originBagsLoaded: number;
  inboundAt: number; landedHkg: boolean;
  rebooked: boolean; rebookedAt: number | null;
  onward: { flight: string; dep: number; arrival: number | null; gate: string | null; seat: string | null;
    terminal: string | null; booked: boolean };
  hkgWalkMin: number; hkgBoarding: number; hkgWalkStart: number; atGateBy: number;
  landed: number | null; border: number | null; belt: number | null; exit: number | null; taxi: number | null;
  hotel: number | null;
  stage: Stage;
};

export function buildStory(trip: Trip, status: ConnectionStatus, nowIso: string): Story {
  const now = instant(nowIso);
  const inbound = status.inbound;
  const origin = inbound.origin;
  const originZone = zoneOf(origin);
  const dest = status.outbound.dest;
  const destZone = zoneOf(dest);
  const inboundSched = instant(inbound.sched);
  const schedDep = inbound.origin_departure ? instant(inbound.origin_departure, originZone) : inboundSched - 5 * 60 * MIN;
  const departed = inbound.origin_departed ? instant(inbound.origin_departed, originZone) : null;
  const leaveHome = schedDep - SAMPLE.leaveBeforeDepartureMin * MIN;
  const checkIn = leaveHome + SAMPLE.driveMin * MIN;
  const security = checkIn + SAMPLE.checkinMin * MIN;
  const originBoarding = schedDep - SAMPLE.boardingBeforeMin * MIN;
  const originWalkStart = originBoarding - (SAMPLE.originWalkMin + SAMPLE.walkBufferMin) * MIN;
  const inboundAt = instant(inbound.actual ?? inbound.est ?? inbound.sched);
  const landedHkg = ["Landed", "At gate"].includes(inbound.status);
  const alt = status.alternative;
  const rebooked = Boolean(alt?.booked) && status.state !== "MADE_ORIGINAL";
  const onward = rebooked && alt
    ? { flight: alt.flight, dep: instant(alt.dep), arrival: alt.final_arrival ? instant(alt.final_arrival, destZone) : null,
        gate: alt.gate, seat: alt.seat, terminal: status.outbound.dest_terminal ?? null, booked: true }
    : { flight: status.outbound.flight, dep: instant(status.outbound.sched),
        arrival: status.outbound.dest_arrival ? instant(status.outbound.dest_arrival, destZone) : null,
        gate: status.outbound.gate, seat: trip.passenger.seat, terminal: status.outbound.dest_terminal ?? null, booked: false };
  const hkgWalkMin = status.walk_to_gate_min ?? SAMPLE.hkgWalkMinDefault;
  const hkgBoarding = onward.dep - SAMPLE.boardingBeforeMin * MIN;
  const hkgWalkStart = hkgBoarding - (hkgWalkMin + SAMPLE.walkBufferMin) * MIN;
  const landed = onward.arrival;
  const border = landed && landed + SAMPLE.borderMin * MIN;
  const belt = landed && landed + SAMPLE.beltAfterLandingMin * MIN;
  const exit = belt && belt + SAMPLE.exitAfterBeltMin * MIN;
  const taxi = exit && exit + SAMPLE.customsMin * MIN;
  const hotel = exit && exit + SAMPLE.hotelDriveMin * MIN;

  let stage: Stage;
  if (now < checkIn) stage = "leave";
  else if (now < security + SAMPLE.walkBufferMin * MIN && !departed) stage = "airport";
  else if (!departed) stage = "insideOrigin";
  else if (!landedHkg) stage = rebooked ? "rebooked" : "flying";
  else if (now < onward.dep) stage = "insideHkg";
  else if (!landed || now < landed) stage = "onward";
  else if (belt && now < belt) stage = "arrive";
  else stage = "exit";

  const p = trip.passenger;
  const last = p.name.split(" ").slice(-1)[0];
  return {
    trip, status, now, name: p.title ? `${p.title} ${last}` : p.name.split(" ")[0],
    origin, originCity: inbound.origin_city, originZone, dest, destCity: status.outbound.dest_city, destZone,
    schedDep, departed, leaveHome, checkIn, security, originBoarding, originWalkStart,
    originBagsLoaded: schedDep - SAMPLE.originBagsLoadedBeforeMin * MIN,
    inboundAt, landedHkg, rebooked, rebookedAt: status.decided_at && rebooked ? instant(status.decided_at) : null,
    onward, hkgWalkMin, hkgBoarding, hkgWalkStart, atGateBy: onward.dep - SAMPLE.atGateBeforeMin * MIN,
    landed, border, belt, exit, taxi, hotel, stage,
  };
}

// REAL: every Cathay departure in the stored HKIA data (2026-08-15 to 2026-11-13) used Terminal 1.
export const HKG_DEPARTURE_TERMINAL = "Terminal 1";

export const CABIN: Record<string, string> = { F: "First", J: "Business", W: "Premium Economy", Y: "Economy" };
