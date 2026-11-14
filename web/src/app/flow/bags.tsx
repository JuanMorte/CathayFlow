// Bags: estimated arrival, tags, status pills and scan timeline (docs/design/s7-bags.png).
// Flight times are REAL; bags, tags, weights and scan times are sample data (sample.ts).
import { Card, HeroCard, Icon, Tag, Timeline, type Step } from "./kit";
import { clock, type View } from "./journey";

export function BagsScreen({ view }: { view: View }) {
  const { sample, status, flight, now, originDeparture, originZone, origin, destZone } = view;
  const city = status.outbound.dest_city;
  const atRisk = status.zone !== "SAFE" && !view.rebooked;
  const belt = flight.arrival ? flight.arrival + sample.firstBags * 60000 : null;
  const checkedIn = originDeparture - 130 * 60000;
  const loaded = originDeparture - 40 * 60000;
  const offPlane = view.inboundAt + sample.bagsOffPlane * 60000;
  const loading = flight.dep - 25 * 60000;
  const steps: Step[] = [
    { title: `Checked in at ${origin}`, detail: clock(checkedIn, originZone), state: "done" },
    { title: `Loaded on ${status.inbound.flight}`, detail: clock(loaded, originZone), state: "done" },
    { title: "Off the plane in Hong Kong", detail: clock(offPlane), state: now >= offPlane ? "done" : "next" },
    { title: `Loading on ${flight.no}`, detail: `Expected ${clock(loading)}${atRisk ? " · priority transfer" : ""}`, state: now >= offPlane ? "now" : "next" },
    { title: `Belt in ${city}`, detail: belt ? `Around ${clock(belt, destZone)}` : "", state: "next" },
  ];
  const last = sample.bags.length - 1;
  return (
    <>
      <HeroCard tag="Bags">
        <p className="text-[15px]">Estimated arrival</p>
        <p className="mt-1 text-[46px] font-bold leading-none">{belt ? clock(belt, destZone) : ""}</p>
        {atRisk && <p className="mt-3 text-[11.5px] text-white/90">Bag {sample.bags.length} is marked for priority handling</p>}
      </HeroCard>
      <div className="mx-4 mt-3 flex flex-col gap-3">
        {sample.bags.map((bag, index) => (
          <Card key={bag.tag} className="px-4 py-[14px]">
            <div className="flex items-center gap-3">
              <span className="flex h-[38px] w-[38px] items-center justify-center rounded-full bg-info text-deep">
                <Icon name="bag" className="h-5 w-5" />
              </span>
              <div className="flex-1">
                <div className="text-[15.5px] font-bold text-ink">Bag {index + 1}</div>
                <div className="text-[13px] text-muted">Tag {bag.tag} · {bag.kg} kg</div>
              </div>
              {index === last && atRisk ? <Tag tone="late" caps={false}>Priority transfer</Tag> : <Tag tone="ok" caps={false}>{now >= offPlane ? `Loading on ${flight.no}` : `On ${status.inbound.flight}`}</Tag>}
            </div>
            {index === last && <div className="mt-3 border-t border-line pt-3"><Timeline steps={steps} /></div>}
          </Card>
        ))}
        <p className="flex items-center gap-[6px] pb-1 text-[12.5px] text-muted">
          <Icon name="info" className="h-4 w-4" /> If a bag ever misses, we deliver it. No desk queue.
        </p>
      </div>
    </>
  );
}
