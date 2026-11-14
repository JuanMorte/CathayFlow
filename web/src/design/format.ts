// Time and number formatting. Times from the API are ISO strings with an offset; Hong Kong times
// are shown in Hong Kong time, destination times (no offset) as given.

const HKT = "Asia/Hong_Kong";

export function hhmm(iso: string | null | undefined): string {
  if (!iso) return "";
  // A destination-local time has no offset: show it exactly as written.
  if (!/[+-]\d{2}:\d{2}$|Z$/.test(iso)) return iso.slice(11, 16);
  return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: HKT, hour12: false });
}

export function dayLabel(iso: string | null | undefined): string {
  if (!iso) return "";
  const local = !/[+-]\d{2}:\d{2}$|Z$/.test(iso);
  const date = new Date(local ? `${iso}Z` : iso);
  return date.toLocaleDateString("en-GB", {
    weekday: "short", day: "numeric", month: "short", timeZone: local ? "UTC" : HKT,
  });
}

export function minutesBetween(from: string, to: string): number {
  return Math.round((new Date(to).getTime() - new Date(from).getTime()) / 60000);
}

export function duration(minutes: number): string {
  const sign = minutes < 0 ? "-" : "";
  const value = Math.abs(minutes);
  const hours = Math.floor(value / 60);
  const rest = value % 60;
  if (!hours) return `${sign}${rest} min`;
  return rest ? `${sign}${hours}h ${rest}m` : `${sign}${hours}h`;
}

export function percent(chance: number): string {
  return `${Math.round(chance * 100)}%`;
}

export function dayOffset(from: string | null | undefined, to: string | null | undefined): number {
  if (!from || !to) return 0;
  const a = Date.UTC(+from.slice(0, 4), +from.slice(5, 7) - 1, +from.slice(8, 10));
  const b = Date.UTC(+to.slice(0, 4), +to.slice(5, 7) - 1, +to.slice(8, 10));
  return Math.round((b - a) / 86400000);
}
