// Connect (in flight): the original flight, still held, and the flight if it is missed
// (docs/design/s5-protect-in-flight.png).
import { useState } from "react";
import type { Option } from "../../api/client";
import { Card, HeroCard, Icon, Notice, PrimaryButton, SecondaryButton, Tag } from "./kit";
import { clock, instant, shortDate, span, type View } from "./journey";

export function ConnectScreen({ view, onChoose, onBags, busy }: {
  view: View; onChoose: (option: Option) => void; onBags: () => void; busy: boolean;
}) {
  const { status, alternative, sample, destZone } = view;
  const [confirming, setConfirming] = useState<Option | null>(null);
  const [kept, setKept] = useState(false);
  const city = status.outbound.dest_city;
  const tight = status.zone !== "SAFE";
  const held = Boolean(status.backup_hold && alternative);
  const approved = Boolean(alternative?.approved);
  const chose = status.state === "PASSENGER_CHOSE";
  const arrival = alternative?.final_arrival ? instant(alternative.final_arrival, destZone) : null;

  if (status.needs_manual_rebooking) {
    return (
      <HeroCard tag="Connect">
        <h1 className="text-[20px] font-bold leading-snug">We're finding you a seat to {city}</h1>
        <p className="mt-3 text-[14px] leading-snug text-white/90">Our team will message you with your new flight.</p>
      </HeroCard>
    );
  }

  return (
    <>
      <HeroCard tag="Connect">
        <h1 className="text-[20px] font-bold leading-snug">
          {tight ? `Your ${city} connection is tight` : `Your ${city} connection looks good`}
        </h1>
        <p className="mt-5 text-[14px] leading-snug text-white/90">
          {status.inbound.flight} {status.inbound.actual ? "reached the gate at" : "now lands"} {clock(view.inboundAt)}
          {view.delayMin >= 5 ? ` (${view.delayMin} min late)` : ""}. The gate for {status.outbound.flight} closes
          at {clock(instant(status.gate_close))}.
        </p>
      </HeroCard>

      <div className="mx-4 mt-3 flex flex-col gap-3">
        {held && alternative && (
          <Notice kind="warn" icon="bell">
            The closest next {city} flight is{" "}
            <b>{span((instant(alternative.dep) - instant(status.outbound.sched)) / 60000)}</b> later.
          </Notice>
        )}

        <h2 className="mt-1 text-[17px] font-bold text-ink">{held ? "Both seats are held for you" : "Your connection"}</h2>

        <Card className="px-4 py-[14px]">
          <div className="flex items-center gap-2">
            <Tag tone="mint">Original · still held</Tag>
          </div>
          <div className="mt-2 text-[16px] font-bold text-ink">
            {status.outbound.flight} · {clock(instant(status.outbound.sched))}
          </div>
          <div className="mt-[2px] text-[13.5px] text-muted">
            Gate {status.outbound.gate ?? "to be confirmed"} · closes {clock(instant(status.gate_close))}
          </div>
          {status.expedite_offered && (
            <div className="mt-2 flex items-center gap-[6px] text-[13px] text-ok">
              <Icon name="check" className="h-4 w-4" /> Fast-track and an escort at the door
            </div>
          )}
          {chose && <div className="mt-2 text-[13px] font-bold text-deep">You're going for this flight</div>}
        </Card>

        {held && alternative && (
          <Card className="px-4 py-[14px]">
            <Tag tone="sand">If you miss it</Tag>
            <div className="mt-2 text-[16px] font-bold text-ink">{alternative.flight} · {clock(instant(alternative.dep))}</div>
            {arrival && (
              <div className="mt-[2px] text-[13.5px] text-muted">
                Lands {city} {clock(arrival, destZone)} {shortDate(arrival, destZone)}
              </div>
            )}
          </Card>
        )}

        <Notice icon="bag" onClick={onBags}>
          Your {sample.bags.length === 1 ? "bag follows" : `${sample.bags.length} bags follow`} whichever flight you take.
        </Notice>

        {kept && <p className="text-center text-[13px] text-deep">Nothing changes unless you choose.</p>}

        {held && alternative && !chose && (
          <div className="flex gap-3 pb-1">
            <PrimaryButton onClick={() => setKept(true)} disabled={busy}>Keep both</PrimaryButton>
            <SecondaryButton onClick={() => setConfirming(alternative)} disabled={!approved || busy}>
              Switch to {alternative.flight}
            </SecondaryButton>
          </div>
        )}
      </div>

      {confirming && (
        <ConfirmSheet view={view} option={confirming} busy={busy} onCancel={() => setConfirming(null)}
          onConfirm={() => { onChoose(confirming); setConfirming(null); }} />
      )}
    </>
  );
}

export function ConfirmSheet({ view, option, busy, onCancel, onConfirm }: {
  view: View; option: Option; busy: boolean; onCancel: () => void; onConfirm: () => void;
}) {
  const arrival = option.final_arrival ? instant(option.final_arrival, view.destZone) : null;
  return (
    <div className="absolute inset-0 z-30 flex items-end bg-black/40" role="dialog" aria-modal="true" onClick={onCancel}>
      <div className="w-full rounded-t-[20px] bg-white p-5 pb-8" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-[18px] font-bold text-ink">Switch to {option.flight}?</h3>
        <p className="mt-2 text-[14px] text-muted">
          {option.flight} leaves at {clock(instant(option.dep))}
          {arrival ? ` and lands ${clock(arrival, view.destZone)} ${shortDate(arrival, view.destZone)}` : ""}. Your seat on{" "}
          {view.status.outbound.flight} goes to someone else.
        </p>
        <div className="mt-4 flex gap-3">
          <SecondaryButton onClick={onCancel} disabled={busy}>Not now</SecondaryButton>
          <PrimaryButton onClick={onConfirm} disabled={busy}>Confirm switch</PrimaryButton>
        </div>
      </div>
    </div>
  );
}
