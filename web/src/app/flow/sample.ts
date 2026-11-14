// DEMO SAMPLE DATA (AGENTS.md non-negotiables 6 and 10, amended 2026-11-13).
//
// The passenger app follows the Cathay design, which shows details that no data source in this
// demo has. They are generated here, deterministically per passenger, and disclosed in README.md:
// Asia Miles and Status Points; terminals, lounge, walking pace, seat numbers; the leave-home
// timeline at the origin; bags (count, tags, weights, scans, belt); arrival details (border wait,
// exit, transport times, hotel area). Times are offsets from REAL flight times.
// Nothing in this file feeds the engine, the policy, the staff console or the evidence.

function hash(text: string): number {
  let value = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    value ^= text.charCodeAt(i);
    value = Math.imul(value, 16777619);
  }
  return value >>> 0;
}

function pick(seed: string, low: number, high: number): number {
  return low + (hash(seed) % (high - low + 1));
}

export type Bag = { tag: string; kg: number };

export type Sample = {
  asiaMiles: number;
  statusPoints: number;
  bags: Bag[];
  originTerminal: string;
  destinationTerminal: string;
  lounge: string;
  newSeat: string;
  /** Minutes before the origin departure for each step of the leave-home timeline. */
  prepare: { leaveHome: number; checkIn: number; security: number; lounge: number; walk: number; boarding: number };
  driveMinutes: number;
  walkToGateMinutes: number;
  /** Minutes after the inbound reaches the gate at Hong Kong. */
  bagsOffPlane: number;
  /** Minutes after landing at the destination. */
  border: number;
  firstBags: number;
  exitBy: number;
  belt: number;
  taxi: number;
  hotelArea: string;
};

const HOTEL_AREAS: Record<string, string[]> = {
  MEL: ["Southbank", "Docklands", "Fitzroy"], SYD: ["The Rocks", "Darling Harbour"], LHR: ["South Kensington", "Covent Garden"],
};

export function sampleFor(pid: string, destination: string): Sample {
  const bagCount = pick(`${pid}:bags`, 1, 2);
  const base = pick(`${pid}:tag`, 410000, 489000);
  const areas = HOTEL_AREAS[destination] ?? ["City centre"];
  return {
    asiaMiles: pick(`${pid}:miles`, 18000, 96000),
    statusPoints: pick(`${pid}:points`, 300, 1200),
    bags: Array.from({ length: bagCount }, (_, i) => ({ tag: `CX ${base + i}`, kg: pick(`${pid}:kg${i}`, 14, 23) })),
    originTerminal: `Terminal ${pick(`${pid}:t1`, 2, 5)}`,
    destinationTerminal: `Terminal ${pick(`${pid}:t2`, 1, 2)}`,
    lounge: "The Pier, Business",
    newSeat: `${pick(`${pid}:row`, 11, 26)}${"ADGK"[pick(`${pid}:col`, 0, 3)]}`,
    prepare: { leaveHome: 180, checkIn: 125, security: 115, lounge: 90, walk: 55, boarding: 40 },
    driveMinutes: pick(`${pid}:drive`, 45, 60),
    walkToGateMinutes: pick(`${pid}:walk`, 9, 14),
    bagsOffPlane: pick(`${pid}:off`, 10, 16),
    border: pick(`${pid}:border`, 15, 25),
    firstBags: pick(`${pid}:belt1`, 25, 35),
    exitBy: pick(`${pid}:exit`, 45, 55),
    belt: pick(`${pid}:belt`, 3, 9),
    taxi: pick(`${pid}:taxi`, 25, 45),
    hotelArea: areas[pick(`${pid}:hotel`, 0, areas.length - 1)],
  };
}
