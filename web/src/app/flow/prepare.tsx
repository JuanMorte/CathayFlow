// Prepare: leave home at, step-by-step origin-airport timeline (docs/design/s3-prepare.png).
// The origin departure is REAL (OAG schedule); the steps before it are sample offsets.
import { Card, HeroCard, Icon, PrimaryButton, SecondaryButton, Timeline, type Step } from "./kit";
import { clock, type View } from "./journey";

export function PrepareScreen({ view }: { view: View }) {
  const { sample, now, originDeparture, originZone, origin, status } = view;
  const at = (minutesBefore: number) => originDeparture - minutesBefore * 60000;
  const p = sample.prepare;
  const marks = [p.leaveHome, p.checkIn, p.security, p.lounge, p.walk, p.boarding].map(at);
  const state = (i: number): Step["state"] => (now >= (marks[i + 1] ?? originDeparture) ? "done" : now >= marks[i] ? "now" : "next");
  const steps: Step[] = [
    { title: "Leave home", detail: `Home → ${origin} ${sample.originTerminal.replace("Terminal ", "T")} · ${sample.driveMinutes} min, live traffic` },
    { title: "Check in", detail: `${status.cabin === "J" ? "Business" : "Check-in"} counter · about ten min` },
    { title: "Immigration and security", detail: "About ten min at this hour" },
    { title: "Lounge time", detail: "Time to relax" },
    { title: "Walk to the gate", detail: `About ${sample.walkToGateMinutes} min at your pace` },
    { title: "Boarding starts", detail: `${status.inbound.flight} departs ${clock(originDeparture, originZone)}` },
  ].map((step, i) => ({ ...step, time: clock(marks[i], originZone), state: state(i) }));
  const until = Math.round((view.leaveHome - now) / 60000);
  return (
    <>
      <HeroCard tag="Prepare">
        <p className="text-[15px]">Leave home at</p>
        <div className="mt-1 flex items-end justify-between">
          <p className="text-[46px] font-bold leading-none">{clock(view.leaveHome, originZone)}</p>
          <span className="mb-1 flex items-center gap-1 rounded-[6px] bg-[#F7E7DA] px-2 py-1 text-[12.5px] font-bold text-late">
            <Icon name="bell" className="h-[14px] w-[14px]" />{until > 0 ? `in ${until} min` : "On your way"}
          </span>
        </div>
      </HeroCard>
      <div className="mx-4 mt-3 flex flex-col gap-3">
        <div className="mt-1 flex items-baseline justify-between">
          <h2 className="text-[17px] font-bold text-ink">Step-by-step journey</h2>
          <span className="text-[13px] text-primary">Updates live</span>
        </div>
        <Card className="p-4"><Timeline steps={steps} timeColumn /></Card>
        <div className="flex gap-3 pb-1">
          <PrimaryButton icon="car">Book a ride</PrimaryButton>
          <SecondaryButton>Remind me {clock(view.leaveHome - 10 * 60000, originZone)}</SecondaryButton>
        </div>
      </div>
    </>
  );
}
