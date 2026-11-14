// Arrival Mode: exit by, border, belt, getting to the hotel (docs/design/s8-arrival.png).
// Landing time is REAL (schedule); border, belt, transport and hotel area are sample data.
import { Card, HeroCard, Icon, Notice, Timeline } from "./kit";
import { clock, type View } from "./journey";

export function ArriveScreen({ view }: { view: View }) {
  const { sample, status, flight, destZone, trip } = view;
  const city = status.outbound.dest_city;
  const landed = flight.arrival;
  const first = trip.passenger.name.split(" ")[0];
  const tiles = [
    { icon: "taxi", title: "Taxi", detail: `~${sample.taxi} min` },
    { icon: "car", title: "Ride-hail", detail: "Open app" },
    { icon: "train", title: "Train", detail: "Rail + bus" },
    { icon: "map", title: "Maps", detail: "Directions" },
  ];
  return (
    <>
      <HeroCard tag="Arrive">
        <h1 className="text-[20px] font-bold">Welcome to {city}</h1>
        <p className="mt-1 flex items-baseline gap-2 text-[15px]">
          Exit by <span className="text-[40px] font-bold leading-none">{view.exit ? clock(view.exit, destZone) : ""}</span>
        </p>
        <p className="mt-2 text-[13.5px]">Collect your bags at <b>Belt {sample.belt}</b></p>
      </HeroCard>
      <div className="mx-4 mt-3 flex flex-col gap-3">
        <Card className="p-4">
          <Timeline steps={[
            { title: `Landed at ${sample.destinationTerminal}`, detail: landed ? clock(landed, destZone) : "", state: "done" },
            { title: "Border control", detail: `About ${sample.border} min right now`, state: "now" },
            { title: `Belt ${sample.belt}`, detail: landed ? `First bags around ${clock(landed + sample.firstBags * 60000, destZone)}, priority first` : "", state: "next" },
            { title: "Customs and exit", detail: "A few minutes", state: "next" },
          ]} />
        </Card>
        <div>
          <h2 className="text-[17px] font-bold text-ink">Getting to your hotel</h2>
          <div className="flex items-center justify-between text-[13px] text-muted">
            <span>{sample.hotelArea}</span>
            <span className="flex items-center gap-1 text-primary"><Icon name="pen" className="h-[14px] w-[14px]" />Edit</span>
          </div>
        </div>
        <div className="grid grid-cols-4 gap-2">
          {tiles.map((tile) => (
            <Card key={tile.title} className="flex flex-col items-center px-1 py-3 text-center">
              <Icon name={tile.icon} className="h-6 w-6 text-deep" />
              <span className="mt-2 text-[13.5px] font-bold text-ink">{tile.title}</span>
              <span className="text-[12px] text-muted">{tile.detail}</span>
            </Card>
          ))}
        </div>
        <Notice icon="exit">
          <b>Flow ends at the airport exit.</b><br />Have a lovely stay, {first}.
        </Notice>
      </div>
    </>
  );
}
