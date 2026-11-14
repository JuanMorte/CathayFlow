// Navigate in the HKG transfer: to the gate, gate close, spare time, route and pier map
// (docs/design/s6-navigate.png). Times come from the engine; walking pace is sample data.
import type { Option } from "../../api/client";
import { Card, HeroCard, HeroStats, Notice, SecondaryButton, Timeline, type Step } from "./kit";
import { HKG_DEPARTURE_TERMINAL, clock, instant, type View } from "./journey";

export function NavigateScreen({ view, onSwitch }: { view: View; onSwitch: (option: Option) => void }) {
  const { status, alternative, sample, now } = view;
  const gate = status.outbound.gate ?? "";
  const close = instant(status.gate_close);
  const ready = instant(status.ready_at_gate.p50);
  const toGate = Math.max(Math.round((ready - view.inboundAt) / 60000), 0);
  const spare = Math.round((close - ready) / 60000);
  const landed = view.inboundAt;
  const screening = landed + Math.max(toGate - sample.walkToGateMinutes, 5) * 60000;
  const state = (from: number, to: number): Step["state"] => (now >= to ? "done" : now >= from ? "now" : "next");
  const steps: Step[] = [
    { title: `Landed at stand ${status.inbound.stand ?? ""}`, detail: clock(landed), state: "done" },
    { title: "Transfer screening", detail: `${clock(screening)} · last checkpoint`, state: state(landed, screening) },
    { title: `Walk to Gate ${gate}`, detail: `About ${sample.walkToGateMinutes} min at your pace`, state: state(screening, ready) },
    { title: `Gate ${gate} · boarding`, detail: `Gate closes ${clock(close)}`, state: now >= ready ? "now" : "next" },
  ];
  return (
    <>
      <HeroCard tag="Navigate">
        <h1 className="text-[20px] font-bold">Head straight to Gate {gate}</h1>
        <HeroStats items={[
          { label: "To the gate", value: `${toGate} min` },
          { label: "Gate closes", value: clock(close) },
          { label: "Spare", value: `${Math.max(spare, 0)} min` },
        ]} />
      </HeroCard>

      <div className="mx-4 mt-3 flex flex-col gap-3">
        <div className="mt-1 flex items-baseline justify-between">
          <h2 className="text-[17px] font-bold text-ink">Your route</h2>
          <span className="text-[12.5px] text-muted">Not to scale</span>
        </div>
        <Card className="flex gap-3 p-4">
          <div className="flex-1"><Timeline steps={steps} /></div>
          <PierMap gate={gate} />
        </Card>
        {alternative && status.backup_hold && (
          <Notice icon="shield">
            Your seat on {alternative.flight} stays held until you board {status.outbound.flight}. Then we release it for others.
          </Notice>
        )}
        {alternative?.approved && (
          <SecondaryButton onClick={() => onSwitch(alternative)}>Need more time? Switch to {alternative.flight}</SecondaryButton>
        )}
      </div>
    </>
  );
}

function PierMap({ gate }: { gate: string }) {
  return (
    <div className="relative flex w-[92px] shrink-0 flex-col items-center rounded-[8px] bg-info py-2">
      <span className="flex h-[22px] w-[22px] items-center justify-center rounded-full border-2 border-deep bg-white text-[10px] font-bold text-deep">{gate}</span>
      <div className="relative my-1 flex w-full flex-1 justify-center">
        <span className="w-[8px] rounded bg-[#A9C6C5]" />
        <span className="absolute inset-y-0 left-1/2 w-0 -translate-x-1/2 border-l-2 border-dashed border-deep" />
        {[0, 1, 2, 3, 4].map((i) => (
          <span key={i} className="absolute flex w-[70px] justify-between" style={{ top: `${12 + i * 20}%` }}>
            <span className="h-[2px] w-[8px] bg-[#8FB1B0]" /><span className="h-[2px] w-[8px] bg-[#8FB1B0]" />
          </span>
        ))}
      </div>
      <span className="text-[10px] text-deep">{HKG_DEPARTURE_TERMINAL.replace("Terminal ", "T")} · Pier</span>
    </div>
  );
}
