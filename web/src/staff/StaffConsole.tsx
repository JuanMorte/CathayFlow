// Flow Ops staff console (/staff), after docs/design/staff-flow-ops.png. Every number carries its
// source label (non-negotiable 6). Staff approve drafted rebookings here (non-negotiable 2).
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api, type ConnectionStatus, type Draft, type InboundSummary, type ReplayState, type Wave } from "../api/client";
import { useLive, type LiveMessage } from "../api/live";
import { dayLabel, duration, hhmm, minutesBetween, percent } from "../design/format";

const CABIN: Record<string, string> = { F: "First", J: "Business", W: "Premium Eco", Y: "Economy" };

function Badge({ label }: { label?: string }) {
  if (!label) return null;
  const style: Record<string, string> = {
    REAL: "bg-ok-bg text-ok", ASSUMED: "bg-warn text-warn-text",
    SYNTHETIC: "bg-[#ECE8F5] text-[#5B4B8A]", SIMULATED: "bg-info text-deep",
  };
  return (
    <span title={`Source: ${label.toLowerCase()}`}
      className={`ml-1 inline-block rounded px-1 align-middle text-[11px] font-bold tracking-wide ${style[label] ?? ""}`}>
      {label}
    </span>
  );
}

function riskColour(chance: number): string {
  return chance >= 0.7 ? "text-late" : chance >= 0.2 ? "text-amber" : "text-ok";
}

function barColour(chance: number): string {
  return chance >= 0.7 ? "bg-late" : chance >= 0.2 ? "bg-amber" : "bg-ok";
}

export function StaffConsole() {
  const [wave, setWave] = useState<Wave | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [replay, setReplay] = useState<ReplayState | null>(null);
  const [hero, setHero] = useState<ConnectionStatus | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<number | undefined>(undefined);

  const refresh = useCallback(async () => {
    try {
      const [nextWave, nextDrafts, nextReplay] = await Promise.all([api.wave(), api.drafts(), api.replayState()]);
      setWave(nextWave);
      setDrafts(nextDrafts);
      setReplay(nextReplay);
      setHero(await api.protect(nextReplay.hero_pid));
      setError(null);
    } catch {
      setError("The demo server is not answering.");
    }
  }, []);

  // Many updates arrive together during play: refresh at most every 400 ms.
  const onMessage = useCallback((message: LiveMessage) => {
    if (message.type === "clock") return;
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(refresh, 400);
  }, [refresh]);
  const { clock, connected } = useLive("role=staff", onMessage);
  const now = clock?.t ?? replay?.t ?? null;
  const playing = clock?.playing ?? replay?.playing ?? false;

  useEffect(() => {
    if (!selected && hero) setSelected(hero.inbound.flight);
  }, [hero, selected]);

  const draftFor = useMemo(() => {
    const map = new Map<string, Draft>();
    for (const draft of drafts) {
      const seen = map.get(draft.connection_id);
      if (!seen || draft.status === "PENDING") map.set(draft.connection_id, draft);
    }
    return map;
  }, [drafts]);

  const inbounds = wave?.summary.inbounds ?? [];
  const inbound = inbounds.find((i) => i.flight === selected) ?? null;
  // The hero's row first, so the demo never has to scroll for it; the rest by chance of missing.
  const rows = (wave?.connections ?? [])
    .filter((row) => !selected || row.inbound.flight === selected)
    .filter((row) => !reviewing || draftFor.get(row.connection_id)?.status === "PENDING")
    .sort((a, b) => Number(b.pid === hero?.pid) - Number(a.pid === hero?.pid));
  const pending = rows.map((row) => draftFor.get(row.connection_id)).filter((d): d is Draft => d?.status === "PENDING");

  const act = async (work: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await work();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "That didn't work.");
    } finally {
      setBusy(false);
    }
  };

  const heroLanding = hero ? hero.inbound.actual ?? hero.inbound.est ?? hero.inbound.sched : null;
  const jump = (minutesBeforeLanding: number) => {
    if (!heroLanding) return;
    const target = new Date(new Date(heroLanding).getTime() - minutesBeforeLanding * 60000);
    act(() => api.control("seek", { t: target.toISOString() }));
  };

  return (
    <div className="min-h-screen bg-staffpage text-ink">
      <header className="flex items-center gap-4 bg-gradient-to-r from-heroFrom to-heroTo px-8 py-4 text-white">
        <span className="rounded-full border border-dashed border-white/70 px-3 py-1 text-[11px] font-bold">CATHAY</span>
        <span className="text-[20px] font-bold">Flow Ops</span>
        <span className="text-[16px] text-white/90">Connection Protect · HKG Transfer</span>
        <div className="ml-auto text-right text-[13px]">
          <div className="font-bold">Transfer desk</div>
          <div>{now ? `${dayLabel(now)} · ${hhmm(now)} HKT` : ""} <Badge label="SIMULATED" /></div>
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-2 border-b border-line bg-white px-8 py-2 text-[13px]">
        <span className="font-bold text-deep">Replay</span>
        <span className={`h-2 w-2 rounded-full ${connected ? "bg-ok" : "bg-saffron"}`} title={connected ? "Live" : "Reconnecting"} />
        <ControlButton onClick={() => act(() => api.control(playing ? "pause" : "play"))} disabled={busy}>
          {playing ? "Pause" : "Play"}
        </ControlButton>
        <ControlButton onClick={() => act(() => api.control("speed", { speed: 60 }))} disabled={busy}>Real minute per second</ControlButton>
        <ControlButton onClick={() => act(() => api.control("speed", { speed: 600 }))} disabled={busy}>Fast</ControlButton>
        <span className="mx-2 h-4 w-px bg-line" />
        <ControlButton onClick={() => act(() => api.control("reset"))} disabled={busy}>Start of day</ControlButton>
        <ControlButton onClick={() => jump(90)} disabled={busy || !heroLanding}>Before landing</ControlButton>
        <ControlButton onClick={() => jump(0)} disabled={busy || !heroLanding}>At landing</ControlButton>
        {hero && (
          <span className="ml-auto text-muted">
            Hero: <b className="text-ink">{hero.passenger_name}</b> · {hero.inbound.flight} → {hero.outbound.flight}
            <Badge label="SYNTHETIC" />
          </span>
        )}
      </div>

      <main className="mx-auto max-w-[1280px] px-8 py-6">
        {error && <p className="mb-4 rounded-[8px] bg-warn px-4 py-2 text-[14px] text-warn-text">{error}</p>}

        <InboundPicker inbounds={inbounds} selected={selected} onSelect={setSelected} />

        {inbound && <InboundCard inbound={inbound} rows={rows} />}

        <section className="mt-5 overflow-hidden rounded-[12px] border border-line bg-white">
          <table className="w-full text-left text-[14px]">
            <thead className="bg-[#F7F6F3] text-[13px] text-muted">
              <tr>
                <th className="px-5 py-3 font-medium">Passenger <Badge label="SYNTHETIC" /></th>
                <th className="px-3 py-3 font-medium">Connection <Badge label="REAL" /></th>
                <th className="px-3 py-3 font-medium">Miss risk <Badge label="SIMULATED" /></th>
                <th className="px-3 py-3 font-medium">Impact</th>
                <th className="px-3 py-3 font-medium">Recommended backup <Badge label="ASSUMED" /></th>
                <th className="px-5 py-3 font-medium" />
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr><td colSpan={6} className="px-5 py-8 text-center text-muted">Nobody on this flight is at risk right now.</td></tr>
              )}
              {rows.map((row) => (
                <Row key={row.connection_id} row={row} draft={draftFor.get(row.connection_id)} busy={busy}
                  hero={row.pid === hero?.pid}
                  onApprove={(id) => act(() => api.decide(id, "approve"))}
                  onReject={(id) => act(() => api.decide(id, "reject", "Kept on original flight by staff"))} />
              ))}
            </tbody>
          </table>
        </section>

        <div className="mt-5 flex flex-wrap items-center gap-4">
          <div className="flex flex-1 items-start gap-3 rounded-[12px] bg-info px-5 py-4 text-[14px]">
            <span className="mt-[2px] text-deep">ⓘ</span>
            <div>
              <div className="font-bold">Seats shared fairly</div>
              <div className="text-muted">
                Assistance needs first, families kept together, then chance of missing; tier only weights it. Held seats
                release when the passenger boards the original flight. Nothing changes for a passenger until they choose.
              </div>
            </div>
          </div>
          <button disabled={busy || pending.length === 0}
            onClick={() => act(() => api.approveBatch(pending.map((d) => d.draft_id)))}
            className="h-[48px] min-w-[220px] rounded-[8px] bg-button px-6 text-[16px] font-medium text-white disabled:opacity-40">
            Approve all ({pending.length})
          </button>
          <button onClick={() => setReviewing(!reviewing)}
            className={`h-[48px] min-w-[140px] rounded-[8px] border-[1.5px] border-primary px-6 text-[16px] font-medium ${reviewing ? "bg-primary text-white" : "bg-white text-primary"}`}>
            {reviewing ? "Show all" : "Review"}
          </button>
        </div>

        {wave && <WaveFooter wave={wave} />}
      </main>
    </div>
  );
}

function ControlButton({ children, onClick, disabled }: { children: ReactNode; onClick: () => void; disabled?: boolean }) {
  return (
    <button onClick={onClick} disabled={disabled}
      className="rounded-[6px] border border-line px-3 py-1 font-medium text-deep hover:bg-info disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-primary">
      {children}
    </button>
  );
}

function InboundPicker({ inbounds, selected, onSelect }: {
  inbounds: InboundSummary[]; selected: string | null; onSelect: (flight: string | null) => void;
}) {
  const busy = inbounds.filter((i) => i.at_risk + i.wont_make > 0);
  return (
    <div className="mb-4 flex flex-wrap gap-2 text-[13px]">
      <button onClick={() => onSelect(null)}
        className={`rounded-full border px-3 py-1 ${selected === null ? "border-deep bg-deep text-white" : "border-line bg-white"}`}>
        Every inbound
      </button>
      {busy.map((i) => (
        <button key={i.flight} onClick={() => onSelect(i.flight)}
          className={`rounded-full border px-3 py-1 ${selected === i.flight ? "border-deep bg-deep text-white" : "border-line bg-white"}`}>
          {i.flight} {i.origin} · {i.at_risk + i.wont_make}
        </button>
      ))}
    </div>
  );
}

function InboundCard({ inbound, rows }: { inbound: InboundSummary; rows: ConnectionStatus[] }) {
  const delay = inbound.delay_min ?? 0;
  const atGate = inbound.actual ?? inbound.est;
  const atRisk = rows.filter((r) => r.zone !== "SAFE").reduce((sum, r) => sum + r.group_size, 0);
  const onward = new Set(rows.filter((r) => r.zone !== "SAFE").map((r) => r.outbound.flight)).size;
  const held = rows.filter((r) => r.backup_hold).reduce((sum, r) => sum + r.group_size, 0);
  const stat = (value: number, label: string, badge: string) => (
    <div className="border-l border-line px-5">
      <div className="text-[30px] font-bold text-deep">{value}</div>
      <div className="text-[13px] text-muted">{label} <Badge label={badge} /></div>
    </div>
  );
  return (
    <section className="flex flex-wrap items-center gap-6 rounded-[12px] border border-line bg-white px-6 py-5">
      <div className="flex-1">
        <span className={`rounded-full px-3 py-1 text-[11px] font-bold tracking-wide ${delay >= 10 ? "bg-[#FBE7DA] text-late" : "bg-ok-bg text-ok"}`}>
          {delay >= 10 ? "INBOUND DELAY" : "INBOUND"}
        </span>
        <h2 className="mt-2 text-[24px] font-bold">{inbound.flight} {inbound.origin_city} → Hong Kong</h2>
        <p className="mt-1 text-[14px] text-muted">
          {inbound.actual ? "At gate" : inbound.est ? "Estimated at gate" : "Scheduled at gate"}{" "}
          {hhmm(atGate ?? inbound.sched)}
          {delay ? ` (${delay > 0 ? "+" : ""}${delay} min)` : ""} · stand {inbound.stand ?? "unknown"} · {inbound.status.toLowerCase()}
          <Badge label="REAL" />
        </p>
      </div>
      <div className="flex">
        {stat(atRisk, "passengers at risk", "SIMULATED")}
        {stat(onward, "onward flights", "REAL")}
        {stat(held, "seats held", "SIMULATED")}
        {stat(inbound.connecting, "connecting", "SYNTHETIC")}
      </div>
    </section>
  );
}

function impactOf(row: ConnectionStatus): { level: "High" | "Medium" | "Low"; why: string } {
  const hold = row.backup_hold;
  const gap = hold ? minutesBetween(row.outbound.sched, hold.dep) : null;
  const next = gap !== null ? `next flight +${duration(gap)}` : "no seat held yet";
  if (row.needs_manual_rebooking) return { level: "High", why: "missed, no seat left" };
  if (row.zone === "SAFE") return { level: "Low", why: "likely to make it" };
  if (row.assistance) return { level: "High", why: "assistance booked" };
  if (row.group_size >= 3) return { level: "High", why: `group of ${row.group_size} · ${next}` };
  if (gap !== null && gap >= 360) return { level: "High", why: next };
  return { level: "Medium", why: next };
}

function Row({ row, draft, busy, hero, onApprove, onReject }: {
  row: ConnectionStatus; draft?: Draft; busy: boolean; hero: boolean;
  onApprove: (id: string) => void; onReject: (id: string) => void;
}) {
  const impact = impactOf(row);
  const hold = row.backup_hold;
  return (
    <tr title={draft?.rationale} className={`border-t border-line align-top ${hero ? "bg-[#EEF5F4]" : ""}`}>
      <td className="px-5 py-3">
        <div className="font-bold">{row.passenger_name}{row.group_size > 1 ? ` (${row.group_size})` : ""}</div>
        <div className="text-[13px] text-muted">
          {row.tier === "None" ? "No tier" : row.tier} · {CABIN[row.cabin] ?? row.cabin}{row.assistance ? " · assistance" : ""}
        </div>
      </td>
      <td className="px-3 py-3">
        <div className="font-bold">{row.outbound.flight} {row.outbound.dest} {hhmm(row.outbound.sched)}</div>
        <div className="text-[13px] text-muted">Gate closes {hhmm(row.gate_close)}</div>
      </td>
      <td className="px-3 py-3">
        <div className={`text-[18px] font-bold ${riskColour(row.p_miss)}`}>{percent(row.p_miss)}</div>
        <div className="mt-1 h-[5px] w-[70px] rounded bg-[#ECEAE6]">
          <div className={`h-[5px] rounded ${barColour(row.p_miss)}`} style={{ width: `${Math.round(row.p_miss * 100)}%` }} />
        </div>
      </td>
      <td className="px-3 py-3">
        <div className={`font-bold ${impact.level === "High" ? "text-late" : impact.level === "Medium" ? "text-amber" : "text-ok"}`}>{impact.level}</div>
        <div className="text-[13px] text-muted">{impact.why}</div>
      </td>
      <td className="px-3 py-3">
        {row.needs_manual_rebooking ? (
          <div className="font-bold text-late">Needs manual rebooking</div>
        ) : hold ? (
          <>
            <div className="font-bold">{hold.flight} {hhmm(hold.dep)}</div>
            <div className="text-[13px] text-muted">{CABIN[hold.cabin] ?? hold.cabin}{row.group_size > 1 ? " · together" : ""}</div>
          </>
        ) : (
          <>
            <div className="font-bold">Monitor only</div>
            <div className="text-[13px] text-muted">no seat held</div>
          </>
        )}
      </td>
      <td className="px-5 py-3 text-right">
        <Action row={row} draft={draft} busy={busy} onApprove={onApprove} onReject={onReject} />
      </td>
    </tr>
  );
}

function Action({ row, draft, busy, onApprove, onReject }: {
  row: ConnectionStatus; draft?: Draft; busy: boolean; onApprove: (id: string) => void; onReject: (id: string) => void;
}) {
  if (row.state === "REBOOKED") return <span className="font-bold text-ok">✓ Rebooked on {row.backup_hold?.flight}</span>;
  if (row.state === "MADE_ORIGINAL") return <span className="font-bold text-ok">✓ Made {row.outbound.flight}</span>;
  if (row.state === "PASSENGER_CHOSE") return <span className="font-bold text-deep">Going for {row.outbound.flight}</span>;
  if (draft?.status === "PENDING") {
    return (
      <div className="flex flex-col items-end gap-1">
        <button onClick={() => onApprove(draft.draft_id)} disabled={busy}
          className="h-[34px] w-[138px] rounded-[6px] bg-button text-[14px] font-medium text-white disabled:opacity-40">Approve</button>
        <button onClick={() => onReject(draft.draft_id)} disabled={busy} className="text-[12px] text-muted underline">Keep on original</button>
      </div>
    );
  }
  if (row.state === "OFFERED") return <span className="font-bold text-ok">✓ Approved</span>;
  if (draft?.status === "REJECTED") return <span className="text-muted">Kept on original</span>;
  return <span className="text-muted">Watching</span>;
}

function WaveFooter({ wave }: { wave: Wave }) {
  const s = wave.summary;
  const item = (value: number, label: string, badge: string) => (
    <span className="whitespace-nowrap">{label} <b className="text-ink">{value}</b><Badge label={badge} /></span>
  );
  return (
    <div className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-[13px] text-muted">
      {item(s.connecting, "Connecting today", "SYNTHETIC")}
      {item(s.at_risk, "At risk", "SIMULATED")}
      {item(s.wont_make, "Won't make it", "SIMULATED")}
      {item(s.holds, "Seats held", "SIMULATED")}
      {item(s.drafts_pending, "Awaiting approval", "SIMULATED")}
      {item(s.rebooked, "Rebooked", "SIMULATED")}
      {item(s.made_original, "Made their flight", "SIMULATED")}
      {item(s.needs_manual_rebooking, "Need manual rebooking", "SIMULATED")}
      <span className="ml-auto">Student concept · Cathay Hackathon · flights real, passengers synthetic</span>
    </div>
  );
}
