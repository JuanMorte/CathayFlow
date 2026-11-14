// New flight confirmed: board in, flight, seat, bags, lounge (docs/design/s7b-plan-b.png).
import { Card, HeroCard, Icon, PrimaryButton } from "./kit";
import { CABIN, HKG_DEPARTURE_TERMINAL, clock, instant, longDate, plusDays, span, type View } from "./journey";

export function PlanBScreen({ view }: { view: View }) {
  const { status, alternative, sample, destZone, now } = view;
  if (!alternative) return null;
  const city = status.outbound.dest_city;
  const dep = instant(alternative.dep);
  const arrival = alternative.final_arrival ? instant(alternative.final_arrival, destZone) : null;
  const wait = Math.max((dep - now) / 60000, 0);
  const hours = Math.floor(wait / 60);
  const plus = arrival ? plusDays(dep, "Asia/Hong_Kong", arrival, destZone) : "";

  return (
    <>
      <HeroCard tag="New flight">
        <p className="text-[15px]">Board {alternative.flight} in</p>
        <p className="mt-1 text-[46px] font-bold leading-none">{hours ? `${hours} hour(s)` : span(wait)}</p>
        {arrival && (
          <p className="mt-3 text-[11.5px] text-white/90">Estimated time arrival at {city}: {clock(arrival, destZone)}</p>
        )}
      </HeroCard>

      <div className="mx-4 mt-3 flex flex-col gap-3">
        <Card className="px-4 py-[14px]">
          <div className="flex items-center gap-[10px] text-[14px] text-ink">
            <span>{longDate(dep)}</span>
            <span className="h-[14px] w-px bg-[#CFCBC4]" />
            <span>{alternative.flight}</span>
          </div>
          <p className="mt-2 text-[18px] font-bold text-deep">Hong Kong <span className="font-normal text-ink">to</span> {city}</p>
          <div className="mt-3 flex items-end">
            <div>
              <div className="text-[15px] font-bold text-deep">HKG</div>
              <div className="text-[31px] leading-tight text-ink">{clock(dep)}</div>
              <div className="text-[12px] text-ink">{HKG_DEPARTURE_TERMINAL}</div>
            </div>
            <div className="relative mx-2 mb-[30px] flex flex-1 items-center text-ink">
              {arrival && (
                <span className="absolute -top-[18px] left-1/2 -translate-x-1/2 whitespace-nowrap text-[12px] text-ink">
                  {span((arrival - dep) / 60000)}
                </span>
              )}
              <Icon name="plane" className="h-[18px] w-[18px] shrink-0 rotate-90" />
              <span className="h-px flex-1 bg-[#B9B5AE]" />
              <span className="h-[7px] w-[7px] rounded-full bg-[#B9B5AE]" />
              {plus && <span className="absolute -right-1 top-[4px] text-[11px] font-bold text-late">{plus}</span>}
            </div>
            <div className="text-right">
              <div className="text-[15px] font-bold text-deep">{status.outbound.dest}</div>
              <div className="text-[31px] leading-tight text-ink">{arrival ? clock(arrival, destZone) : ""}</div>
              <div className="text-[12px] text-ink">{sample.destinationTerminal}</div>
            </div>
          </div>
        </Card>

        <Card className="flex flex-col px-4 py-1">
          <Row icon="seat" title={`Seat ${sample.newSeat}`} detail={`${CABIN[alternative.cabin] ?? alternative.cabin} · window seat`} />
          <Row icon="bag" title={sample.bags.length === 1 ? `Your bag is moved to ${alternative.flight}` : `Both bags moved to ${alternative.flight}`}
            detail="Belt number to be confirmed" />
          <Row icon="cup" title={sample.lounge} detail="We'll tell you when to head to the gate" last />
        </Card>

        <PrimaryButton>View boarding passes</PrimaryButton>
      </div>
    </>
  );
}

function Row({ icon, title, detail, last }: { icon: string; title: string; detail: string; last?: boolean }) {
  return (
    <div className={`flex items-center gap-3 py-3 ${last ? "" : "border-b border-line"}`}>
      <span className="flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-full bg-info text-deep">
        <Icon name={icon} className="h-5 w-5" />
      </span>
      <div className="flex-1">
        <div className="text-[15px] font-bold text-ink">{title}</div>
        <div className="text-[13px] text-muted">{detail}</div>
      </div>
      <Icon name="check" className="h-5 w-5 text-ok" />
    </div>
  );
}
