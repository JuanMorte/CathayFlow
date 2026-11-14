// Gate Planner (Travel tools): when to leave for the airport, for a flight departing Hong Kong
// (AGENTS.md §12). Laid out like Prepare (docs/design/s3-prepare.png); re-plans as the replay runs.
import { useEffect, useRef, useState, type ReactNode } from "react";
import { api, type PlannerOptions, type PlannerRequest, type PlannerResult } from "../../api/client";
import { Card, HeroCard, Icon, Notice } from "./kit";
import { clock, instant } from "./journey";

const MODES = [{ id: "car", label: "Car or taxi" }, { id: "train", label: "MTR" }, { id: "bus", label: "Bus" }] as const;
const MARGINS = [{ id: "relaxed", label: "Relaxed" }, { id: "balanced", label: "Balanced" }, { id: "tight", label: "Tight" }] as const;

export function PlannerScreen({ nowIso }: { nowIso: string }) {
  const [options, setOptions] = useState<PlannerOptions | null>(null);
  const [request, setRequest] = useState<PlannerRequest | null>(null);
  const [result, setResult] = useState<PlannerResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const lastPlanned = useRef(0);

  useEffect(() => {
    api.plannerOptions().then((next) => {
      setOptions(next);
      setRequest((current) => current ?? {
        origin_id: next.origins[0]?.id ?? "central",
        flight_key: (next.flights.find((f) => instant(f.sched) - instant(next.t) >= 3 * 3600000) ?? next.flights[0])?.key ?? "",
        bags: 1, checked_in_online: false, hk_resident: true, mode: "car", buffer: "balanced",
      });
    }).catch(() => setError("The planner is not answering."));
  }, []);

  // Plan now, and again as the replay clock moves: at most every three seconds, but a change that
  // arrives inside that window is planned when it ends, never dropped.
  useEffect(() => {
    if (!request?.flight_key) return;
    const run = () => {
      lastPlanned.current = Date.now();
      api.plan(request).then((next) => { setResult(next); setError(null); })
        .catch(() => setError("Couldn't make a plan for that flight."));
    };
    const wait = 3000 - (Date.now() - lastPlanned.current);
    if (wait <= 0) {
      run();
      return;
    }
    const timer = window.setTimeout(run, wait);
    return () => window.clearTimeout(timer);
  }, [request, nowIso]);

  const update = (change: Partial<PlannerRequest>) => {
    lastPlanned.current = 0;
    setRequest((current) => (current ? { ...current, ...change } : current));
  };
  const minutesLeft = result ? Math.round((instant(result.leave_by) - instant(nowIso)) / 60000) : 0;

  return (
    <>
      <HeroCard tag="Gate Planner">
        <p className="text-[15px]">Leave by</p>
        <div className="mt-1 flex items-end justify-between">
          <p className="text-[46px] font-bold leading-none">{result ? clock(instant(result.leave_by)) : "–"}</p>
          {result && (
            <span className="mb-1 flex items-center gap-1 rounded-[6px] bg-[#F7E7DA] px-2 py-1 text-[12.5px] font-bold text-late">
              <Icon name="bell" className="h-[14px] w-[14px]" />{minutesLeft > 0 ? `in ${minutesLeft} min` : "Leave now"}
            </span>
          )}
        </div>
        {result && (
          <p className="mt-3 text-[12px] text-white/90">
            {result.deadline_kind} {clock(instant(result.deadline))} · {result.flight} to {result.dest_city}
            {result.gate ? ` · gate ${result.gate}` : ""}
          </p>
        )}
      </HeroCard>

      <div className="mx-4 mt-3 flex flex-col gap-3">
        {options && request && (
          <Card className="flex flex-col gap-3 p-4 text-[14px] text-ink">
            <Field label="From">
              <select value={request.origin_id} onChange={(e) => update({ origin_id: e.target.value })}
                className="w-full rounded-[8px] border border-line bg-white px-2 py-2">
                {options.origins.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
              </select>
            </Field>
            <Field label="Flight">
              <select value={request.flight_key} onChange={(e) => update({ flight_key: e.target.value })}
                className="w-full rounded-[8px] border border-line bg-white px-2 py-2">
                {options.flights.map((f) => (
                  <option key={f.key} value={f.key}>{f.flight} · {clock(instant(f.sched))} · {f.dest_city}</option>
                ))}
              </select>
            </Field>
            <Field label="Checked bags">
              <div className="flex items-center gap-3">
                <Stepper label="Fewer bags" onClick={() => update({ bags: Math.max((request.bags ?? 0) - 1, 0) })}>−</Stepper>
                <span className="w-5 text-center font-bold">{request.bags ?? 0}</span>
                <Stepper label="More bags" onClick={() => update({ bags: Math.min((request.bags ?? 0) + 1, 4) })}>+</Stepper>
              </div>
            </Field>
            <Toggle label="Checked in online" on={Boolean(request.checked_in_online)} onChange={(v) => update({ checked_in_online: v })} />
            <Toggle label="Hong Kong resident (e-Channel)" on={Boolean(request.hk_resident)} onChange={(v) => update({ hk_resident: v })} />
            <Field label="Getting there">
              <Segmented items={MODES} value={request.mode ?? "car"} onChange={(v) => update({ mode: v as PlannerRequest["mode"] })} />
            </Field>
            <Field label="Margin">
              <Segmented items={MARGINS} value={request.buffer ?? "balanced"} onChange={(v) => update({ buffer: v as PlannerRequest["buffer"] })} />
            </Field>
          </Card>
        )}

        {result && (
          <>
            <div className="mt-1 flex items-baseline justify-between">
              <h2 className="text-[17px] font-bold text-ink">Door to gate</h2>
              <span className="text-[13px] text-primary">Updates live</span>
            </div>
            <Card className="px-4 py-1">
              {result.steps.map((step, i) => (
                <div key={step.key} className={`flex items-start gap-3 py-3 ${i < result.steps.length - 1 ? "border-b border-line" : ""}`}>
                  <div className="flex-1">
                    <div className="text-[15px] font-bold text-ink">{step.title}</div>
                    <div className="text-[12.5px] text-muted">{step.note}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-[15px] font-bold text-deep">{step.typical} min</div>
                    <div className="text-[12px] text-muted">up to {step.upper}</div>
                  </div>
                </div>
              ))}
            </Card>
            <p className="text-[12.5px] text-muted">
              Usually {result.typical_total} min door to gate, up to {result.upper_total} on a bad day. The plan covers
              the slower end of that range.
            </p>
            {result.nudges.map((nudge) => <Notice key={nudge} icon="info">{nudge}</Notice>)}
          </>
        )}
        {error && <p className="rounded-[8px] bg-warn px-3 py-2 text-[13px] text-warn-text">{error}</p>}
      </div>
    </>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[12.5px] font-bold text-muted">{label}</span>
      {children}
    </label>
  );
}

function Stepper({ label, onClick, children }: { label: string; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" aria-label={label} onClick={onClick}
      className="flex h-8 w-8 items-center justify-center rounded-full border border-primary text-[18px] text-primary">
      {children}
    </button>
  );
}

function Toggle({ label, on, onChange }: { label: string; on: boolean; onChange: (value: boolean) => void }) {
  return (
    <div className="flex items-center justify-between">
      <span>{label}</span>
      <button type="button" role="switch" aria-checked={on} aria-label={label} onClick={() => onChange(!on)}
        className={`flex h-[28px] w-[46px] items-center rounded-full p-[3px] ${on ? "justify-end bg-primary" : "justify-start bg-[#CFCBC4]"}`}>
        <span className="h-[22px] w-[22px] rounded-full bg-white shadow" />
      </button>
    </div>
  );
}

function Segmented({ items, value, onChange }: {
  items: readonly { id: string; label: string }[]; value: string; onChange: (value: string) => void;
}) {
  return (
    <div className="flex rounded-[8px] border border-line p-[3px]">
      {items.map((item) => (
        <button key={item.id} type="button" onClick={() => onChange(item.id)}
          className={`flex-1 rounded-[6px] px-2 py-[6px] text-[13px] ${value === item.id ? "bg-deep font-bold text-white" : "text-ink"}`}>
          {item.label}
        </button>
      ))}
    </div>
  );
}
