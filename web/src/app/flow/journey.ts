// Turns API data into what the passenger screens show. Flight times come from the API (REAL); the
// details listed in sample.ts are offsets from them.
import type { ConnectionStatus, Option, Trip } from "../../api/client";
import { sampleFor, type Sample } from "./sample";
import type { Stop } from "./kit";

const HKT = "Asia/Hong_Kong";
// Local time zones for the airports a traveller may start or end at.
const ZONES: Record<string, string> = {
  LHR: "Europe/London", MAN: "Europe/London", CDG: "Europe/Paris", AMS: "Europe/Amsterdam",
  FRA: "Europe/Berlin", MUC: "Europe/Berlin", ZRH: "Europe/Zurich", MXP: "Europe/Rome", FCO: "Europe/Rome",
  MAD: "Europe/Madrid", BCN: "Europe/Madrid", BRU: "Europe/Brussels", JFK: "America/New_York",
  BOS: "America/New_York", ORD: "America/Chicago", DFW: "America/Chicago", LAX: "America/Los_Angeles",
  SFO: "America/Los_Angeles", SEA: "America/Los_Angeles", YVR: "America/Vancouver", YYZ: "America/Toronto",
  SYD: "Australia/Sydney", MEL: "Australia/Melbourne", BNE: "Australia/Brisbane", PER: "Australia/Perth",
  AKL: "Pacific/Auckland", CHC: "Pacific/Auckland", SIN: "Asia/Singapore", BKK: "Asia/Bangkok",
  CGK: "Asia/Jakarta", TPE: "Asia/Taipei", NRT: "Asia/Tokyo", HND: "Asia/Tokyo", ICN: "Asia/Seoul",
};

export const zoneOf = (airport: string) => ZONES[airport] ?? HKT;

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
  const local = Date.UTC(+parts.year, +parts.month - 1, +parts.day, +parts.hour, +parts.minute, +parts.second);
  return local - at;
}

export const clock = (ms: number, zone = HKT) =>
  new Date(ms).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: zone });

export const longDate = (ms: number, zone = HKT) =>
  `${shortDate(ms, zone)} ${new Date(ms).toLocaleDateString("en-GB", { year: "numeric", timeZone: zone })}`;

export const shortDate = (ms: number, zone = HKT) =>
  new Date(ms).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short", timeZone: zone }).replace(",", "");

export const fullDate = (ms: number, zone = HKT) =>
  new Date(ms).toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", timeZone: zone });

/** "+1" when `ms` falls on a later local calendar day than `from` does (each in its own zone). */
export function plusDays(from: number, fromZone: string, ms: number, zone: string): string {
  const day = (t: number, z: string) => Date.parse(`${new Date(t + offsetMs(t, z)).toISOString().slice(0, 10)}T00:00:00Z`);
  const days = Math.round((day(ms, zone) - day(from, fromZone)) / 86400000);
  return days > 0 ? `+${days}` : "";
}

export function span(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return h ? `${h}h ${m}m` : `${m} min`;
}

export type Stage = "prepare" | "connect" | "navigate" | "planb";

export type View = {
  trip: Trip;
  status: ConnectionStatus;
  sample: Sample;
  now: number;
  original?: Option;
  alternative?: Option;
  overnight?: Option;
  rebooked: boolean;
  origin: string;
  dest: string;
  originZone: string;
  destZone: string;
  originDeparture: number;     // REAL schedule (OAG) when known
  leaveHome: number;           // sample offset
  inboundAt: number;           // best known gate arrival at HKG
  delayMin: number;
  flight: { no: string; dep: number; arrival: number | null };  // the onward flight the traveller is on now
  exit: number | null;
  stage: Stage;
};

export function buildView(trip: Trip, status: ConnectionStatus, options: Option[], nowIso: string): View {
  const inbound = status.inbound;
  const origin = inbound.origin;
  const dest = status.outbound.dest;
  const originZone = zoneOf(origin);
  const destZone = zoneOf(dest);
  const sample = sampleFor(trip.passenger.pid, dest);
  const original = options.find((o) => o.kind === "ORIGINAL_EXPEDITE");
  const alternative = options.find((o) => o.kind === "ALT_FLIGHT");
  const overnight = options.find((o) => o.kind === "OVERNIGHT");
  const rebooked = status.state === "REBOOKED";
  const now = instant(nowIso);
  const inboundAt = instant(inbound.actual ?? inbound.est ?? inbound.sched);
  const sched = instant(inbound.sched);
  const delayMin = inbound.actual || inbound.est ? Math.round((inboundAt - sched) / 60000) : 0;
  const originDeparture = inbound.origin_departure ? instant(inbound.origin_departure, originZone) : sched - 13 * 3600000;
  const onward = rebooked && alternative ? alternative : original;
  const arrivalLocal = onward?.final_arrival ?? status.outbound.dest_arrival ?? null;
  const arrival = arrivalLocal ? instant(arrivalLocal, destZone) : null;
  const flight = { no: onward?.flight ?? status.outbound.flight, dep: instant(onward?.dep ?? status.outbound.sched), arrival };
  const landed = ["Landed", "At gate"].includes(inbound.status);
  const stage: Stage = rebooked ? "planb" : landed ? "navigate" : now < originDeparture ? "prepare" : "connect";
  return {
    trip, status, sample, now, original, alternative, overnight, rebooked, origin, dest, originZone, destZone,
    originDeparture, leaveHome: originDeparture - sample.prepare.leaveHome * 60000, inboundAt, delayMin,
    flight, exit: arrival ? arrival + sample.exitBy * 60000 : null, stage,
  };
}

export function strip(view: View, open: (screen: string) => void, at?: "arrive") {
  const { now, originDeparture, inboundAt, flight, exit, origin, dest, originZone, destZone } = view;
  const plus = (ms: number) => plusDays(inboundAt, HKT, ms, destZone);
  const stops: Stop[] = [
    { code: "Home", time: clock(view.leaveHome, originZone), onTap: () => open("prepare") },
    { code: origin, time: clock(originDeparture, originZone), onTap: () => open("prepare") },
    { code: "HKG", time: clock(inboundAt), late: view.delayMin >= 10, onTap: () => open("hkg") },
    { code: dest, time: flight.arrival ? `${clock(flight.arrival, destZone)}${plus(flight.arrival)}` : "", late: view.rebooked, onTap: () => open("arrive") },
    { code: "Exit", time: exit ? `${clock(exit, destZone)}${plus(exit)}` : "", late: view.rebooked, onTap: () => open("arrive") },
  ];
  if (at === "arrive") return { stops, done: 3, here: 3, progress: 3, flying: false };
  if (view.stage === "prepare") {
    const left = now >= view.leaveHome ? 1 : 0;
    return { stops, done: left, here: left, progress: left, flying: false };
  }
  if (view.stage === "connect") {
    const share = Math.min(Math.max((now - originDeparture) / Math.max(inboundAt - originDeparture, 1), 0.08), 0.92);
    return { stops, done: 2, here: null, progress: 1 + share, flying: true };
  }
  return { stops, done: 2, here: 2, progress: 2, flying: false };
}

export const CABIN: Record<string, string> = { F: "First", J: "Business", W: "Premium Economy", Y: "Economy" };

// REAL: every Cathay departure in the stored HKIA data (2026-08-15 to 2026-11-13) used Terminal 1.
export const HKG_DEPARTURE_TERMINAL = "Terminal 1";
