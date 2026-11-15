// Flow Ops (/staff), after the Figma frame "S4 Agent dashboard". An agent decides each drafted
// rebooking: Rebook books the later flight and tells the passenger; the original seat stays held until
// its gate closes (AGENTS.md §2). Replay controls for the demo sit below the design's layout.
import { useCallback, useMemo, useRef, useState } from "react";
import { api, type ConnectionStatus, type Draft, type ReplayState, type Wave } from "../api/client";
import { useLive, type LiveMessage } from "../api/live";
import iconPlane from "../assets/flow/icon-plane.png";
import { CABIN, clock, instant, longDate, zoneOf } from "../app/flow/journey";

const AGENT = "S. Alicia";
const shortName = (name: string) => {
  const parts = name.split(" ");
  return `${parts[parts.length - 1]}, ${parts[0][0]}.`;
};
const window_ = (seat: string | null) => (!seat ? "" : /[AK]$/.test(seat) ? `, window` : /[CDGH]$/.test(seat) ? ", aisle" : "");
const later = (hours: number) => {
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  return m ? `${h} h ${m} later` : `${h} h later`;
};

export function StaffConsole() {
  const [wave, setWave] = useState<Wave | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [replay, setReplay] = useState<ReplayState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<number | undefined>(undefined);

  const refresh = useCallback(async () => {
    try {
      const [nextWave, nextDrafts, nextReplay] = await Promise.all([api.wave(true), api.drafts(), api.replayState()]);
      setWave(nextWave);
      setDrafts(nextDrafts);
      setReplay(nextReplay);
      setError(null);
    } catch {
      setError("The demo server is not answering.");
    }
  }, []);
  const onMessage = useCallback((message: LiveMessage) => {
    if (message.type === "clock") return;
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(refresh, 300);
  }, [refresh]);
  const { clock: live, connected } = useLive("role=staff", onMessage);
  const now = live?.t ?? replay?.t ?? null;
  const playing = live?.playing ?? replay?.playing ?? false;

  const draftFor = useMemo(() => {
    const map = new Map<string, Draft>();
    for (const d of drafts) if (!map.get(d.connection_id) || d.status === "PENDING") map.set(d.connection_id, d);
    return map;
  }, [drafts]);

  // The inbound flight with the most passengers at risk.
  const inbound = [...(wave?.summary.inbounds ?? [])].sort((a, b) => (b.at_risk + b.wont_make) - (a.at_risk + a.wont_make)
    || b.connecting - a.connecting)[0];
  const rows = (wave?.connections ?? []).filter((r) => r.inbound.flight === inbound?.flight);
  const pendingOf = (r: ConnectionStatus) => draftFor.get(r.connection_id)?.status === "PENDING";
  rows.sort((a, b) => Number(pendingOf(b)) - Number(pendingOf(a))
    || (a.decided_at ?? "").localeCompare(b.decided_at ?? "") || b.p_miss - a.p_miss);
  const atRisk = rows.filter((r) => r.zone !== "SAFE").length;
  const onwardFlights = new Set(rows.map((r) => r.outbound.flight)).size;
  const rebooked = rows.filter((r) => r.decision === "REBOOK").length;
  const waiting = rows.filter(pendingOf).length;
  const sample = rows[0]?.inbound;

  const act = async (work: () => Promise<unknown>) => {
    setBusy(true);
    try { await work(); await refresh(); } catch (err) { setError(err instanceof Error ? err.message : "That didn't work."); } finally { setBusy(false); }
  };
  const seek = (iso: string) => act(() => api.control("seek", { t: iso }));
  const nowMs = now ? instant(now) : null;

  return (
    <div className="min-h-screen bg-[#F7F6F3] font-jost text-black">
      <header className="flex items-center border-b border-[#E6E6E6] bg-white px-8 py-[18px]">
        <span className="text-[24px]">Flow Ops</span>
        <span className="ml-[13px] mt-[4px] text-[14px] text-muted">Connection decisions</span>
        <div className="ml-auto text-right">
          <div className="text-[15px] font-bold">Agent: {AGENT}</div>
          <div className="text-[12.5px] text-muted">{nowMs ? `${longDate(nowMs).split(" ").slice(0, 3).join(" ")}, ${clock(nowMs)} HKT` : ""}</div>
        </div>
      </header>

      <main className="mx-auto max-w-[1280px] px-8 pb-10 pt-6">
        {error && <p className="mb-4 rounded-[8px] bg-warn px-4 py-2 text-[14px] text-warn-text">{error}</p>}
        {inbound && sample && (
          <section className="rounded-[15px] bg-white shadow-[0_0_20px_rgba(0,0,0,0.05)]">
            <div className="flex px-4 pt-[14px]">
              <div className="w-[560px] pr-6">
                <div className="flex items-center text-[12.5px] font-light">
                  <span>{longDate(instant(inbound.sched))}</span>
                  {(inbound.delay_min ?? 0) >= 15 && <><span className="mx-[9px] h-[14px] w-px bg-[#BDBDBD]" /><span className="text-late">Inbound delay</span></>}
                </div>
                <div className="mt-[2px] text-[20px]">
                  <span className="font-bold text-primary">{inbound.flight}</span> {inbound.origin_city} <span>to</span> <span className="font-bold text-primary">Hong Kong</span>
                </div>
                <div className="mt-[8px] flex justify-between text-[15px] font-bold text-primary"><span>{inbound.origin}</span><span>HKG</span></div>
                <div className="flex items-center">
                  <span className="w-[80px] text-[26px]">{sample.origin_departed ? clock(instant(sample.origin_departed, zoneOf(inbound.origin)), zoneOf(inbound.origin)) : "–"}</span>
                  <div className="relative mx-2 h-[30px] flex-1">
                    <div className="absolute left-[24px] right-0 top-1/2 h-px bg-[#D9D9D9]" />
                    <img src={iconPlane} alt="" className="absolute left-0 top-1/2 h-[18px] w-[18px] -translate-y-1/2 brightness-0" />
                    <span className="absolute right-0 top-1/2 h-[8px] w-[8px] -translate-y-1/2 rounded-full bg-[#D9D9D9]" />
                    {inbound.delay_min != null && inbound.delay_min > 0 && (
                      <span className="absolute -top-[10px] left-1/2 -translate-x-1/2 text-[12.5px] text-late">+{inbound.delay_min} min late</span>
                    )}
                  </div>
                  <span className="w-[80px] text-right text-[26px]">{clock(instant(inbound.actual ?? inbound.est ?? inbound.sched))}</span>
                </div>
                <div className="flex justify-between text-[11px] font-light">
                  <span>{sample.origin_departed ? "Departed" : "Scheduled"}{sample.origin_departure ? `, planned ${clock(instant(sample.origin_departure, zoneOf(inbound.origin)), zoneOf(inbound.origin))}` : ""}</span>
                  <span>{inbound.actual ? "On-block" : "Predicted on-block"}</span>
                </div>
              </div>
              <div className="flex flex-1">
                {[[atRisk, "passengers at risk"], [onwardFlights, "onward flights"], [rebooked, "rebooked"], [waiting, "waiting for you"]].map(([value, label]) => (
                  <div key={label as string} className="flex-1 border-l border-[#E2E2E2] pl-[22px] pt-[56px]">
                    <div className="text-[34px] leading-none text-primary">{value}</div>
                    <div className="mt-[8px] text-[13px] text-black">{label}</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="mt-[24px] flex items-center border-t border-[#E2E2E2] px-4 py-[14px]">
              <span className="text-[13px] font-light">Predicted from live flight position, updated {nowMs ? clock(nowMs) : ""}</span>
              <button className="ml-auto rounded-[8px] border border-primary px-[34px] py-[8px] text-[14px] text-primary">View flight</button>
            </div>
          </section>
        )}

        <h2 className="mt-[22px] text-[22px]">{waiting ? "Needs your decision" : "Connections on this flight"}</h2>
        <section className="mt-[14px] rounded-[15px] bg-white px-4 pb-2 shadow-[0_0_20px_rgba(0,0,0,0.05)]">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-[#E2E2E2] text-[13px] text-black/80">
                <th className="w-[46px]" /><th className="py-[14px] font-normal">Passenger</th><th className="font-normal">Connection</th>
                <th className="font-normal">Miss risk</th><th className="font-normal">Why it matters</th><th className="font-normal">Flow suggests</th>
                <th className="text-right font-normal">Decision</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <DecisionRow key={row.connection_id} row={row} draft={draftFor.get(row.connection_id)} busy={busy}
                  onDecide={(id, decision) => act(() => api.decide(id, decision, decision === "reject" ? "Kept on the original flight" : undefined))} />
              ))}
              {!rows.length && <tr><td colSpan={7} className="py-6 text-center text-[14px] text-muted">No connections at risk right now.</td></tr>}
            </tbody>
          </table>
        </section>

        <div className="mt-8 flex flex-wrap items-center gap-2 rounded-[10px] border border-dashed border-[#CFCBC4] bg-white/60 px-4 py-2 text-[13px] text-muted">
          <span className="font-bold text-ink">Demo replay</span>
          <span className={`h-2 w-2 rounded-full ${connected ? "bg-ok" : "bg-saffron"}`} />
          <span>{nowMs ? `${longDate(nowMs)} ${clock(nowMs)} HKT` : ""}{replay?.illustrative ? " · scripted story" : ""}</span>
          <Ctl onClick={() => act(() => api.control(playing ? "pause" : "play"))} disabled={busy}>{playing ? "Pause" : "Play"}</Ctl>
          <Ctl onClick={() => act(() => api.control("speed", { speed: 60 }))} disabled={busy}>Normal speed</Ctl>
          <Ctl onClick={() => act(() => api.control("speed", { speed: 1200 }))} disabled={busy}>Fast</Ctl>
          <Ctl onClick={() => act(() => api.control("reset"))} disabled={busy}>Start of day</Ctl>
          {replay?.illustrative && (
            <>
              {[["Leave home", "06:05"], ["At the airport", "07:10"], ["Decision time", "13:46"], ["Landed", "15:35"], ["Arrived", "14:05"]].map(([label, t], i) => (
                <Ctl key={label} disabled={busy} onClick={() => seek(`${replay.start.slice(0, 8)}${i === 4 ? "16" : "15"}T${t}:00+08:00`)}>{label}</Ctl>
              ))}
            </>
          )}
        </div>
      </main>
    </div>
  );
}

function Ctl({ children, onClick, disabled }: { children: React.ReactNode; onClick: () => void; disabled?: boolean }) {
  return <button onClick={onClick} disabled={disabled} className="rounded-[6px] border border-[#CFCBC4] bg-white px-2 py-1 text-ink hover:bg-info disabled:opacity-40">{children}</button>;
}

function DecisionRow({ row, draft, busy, onDecide }: {
  row: ConnectionStatus; draft?: Draft; busy: boolean; onDecide: (id: string, decision: "approve" | "reject") => void;
}) {
  const alt = row.alternative;
  const out = row.outbound;
  const gateClose = clock(instant(row.gate_close));
  const who = row.assistance_note ?? [row.tier, CABIN[row.cabin], row.bags && row.bags > 1 ? `${row.bags} bags` : null].filter(Boolean).join(", ");
  const why = row.assistance
    ? ["Assistance must move too", "Needs a booked helper"]
    : row.zone === "SAFE" ? ["Likely to make it", alt ? "Backup held, just in case" : `${row.minutes_available} min to reach the gate`]
      : alt ? [`Next ${alt.dest_city} flight`, later(alt.hours_later)] : ["No later flight", "Needs manual rebooking"];
  const suggest = draft || alt
    ? [`Rebook ${alt?.flight ?? draft?.alt_flight} ${clock(instant(alt?.dep ?? draft!.alt_dep))}`,
       row.assistance ? "Aisle seat + assist" : alt?.seat ? `Seat ${alt.seat}${window_(alt.seat)}` : ""]
    : [`Keep ${out.flight}`, row.expedite_offered ? "Fast-transfer route" : "On time so far"];
  const risk = Math.round(row.p_miss * 100);
  let decision;
  if (row.outcome === "MADE") decision = <span className="text-[15px] text-muted">Made {out.flight}</span>;
  else if (row.decision === "REBOOK") decision = <span className="text-[15px] text-primary">Rebooked {row.decided_at ? clock(instant(row.decided_at)) : ""}</span>;
  else if (row.decision === "KEEP") decision = <span className="text-[15px] text-muted">Kept on {out.flight}</span>;
  else if (draft?.status === "PENDING") {
    decision = (
      <span className="inline-flex gap-[12px]">
        <button disabled={busy} onClick={() => onDecide(draft.draft_id, "reject")}
          className="h-[40px] w-[70px] rounded-[8px] border border-primary text-[14px] text-primary disabled:opacity-40">Keep</button>
        <button disabled={busy} onClick={() => onDecide(draft.draft_id, "approve")}
          className="h-[40px] w-[80px] rounded-[8px] bg-[#2C4035] text-[14px] text-white disabled:opacity-40">Rebook</button>
      </span>
    );
  } else decision = <span className="text-[15px] text-muted">Watching</span>;
  return (
    <tr className="border-b border-[#EEEEEE] last:border-0">
      <td className="py-[14px]">
        <span className="flex h-[34px] w-[34px] items-center justify-center rounded-full bg-[#F1F1F1] text-primary">
          <svg viewBox="0 0 24 24" className="h-[16px] w-[16px]" fill="currentColor" aria-hidden="true"><path d="M12 12a4.5 4.5 0 1 0 0-9 4.5 4.5 0 0 0 0 9zm-8 9a8 8 0 0 1 16 0z" /></svg>
        </span>
      </td>
      <td><div className="text-[16px] font-bold">{shortName(row.passenger_name)}</div><div className="text-[13px] text-muted">{who}</div></td>
      <td><div className="text-[16px] font-bold">{out.flight} {out.dest} {clock(instant(out.sched))}</div><div className="text-[13px] text-muted">Gate closes {gateClose}</div></td>
      <td className={`text-[16px] ${row.zone === "SAFE" ? "text-primary" : "text-late"}`}>{risk}%</td>
      <td><div className="text-[16px] font-bold">{why[0]}</div><div className="text-[13px] text-muted">{why[1]}</div></td>
      <td><div className="text-[16px] font-bold">{suggest[0]}</div><div className="text-[13px] text-muted">{suggest[1]}</div></td>
      <td className="text-right">{decision}</td>
    </tr>
  );
}
