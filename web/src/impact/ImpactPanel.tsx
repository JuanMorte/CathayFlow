// Impact panel (/impact): data/evidence.json, built by the backtest and the policy replay.
// Every figure shows its label and source (non-negotiable 6).
import { useEffect, useState } from "react";
import { api, type ImpactMetric } from "../api/client";

const SECTIONS: { title: string; lead: string; ids: string[] }[] = [
  {
    title: "Tight connections break, and a miss is costly",
    lead: "Every Cathay-operated flight at Hong Kong over three months.",
    ids: ["break_rate_normal", "break_rate_disrupted", "next_flight_hours", "next_flight_6h"],
  },
  {
    title: "Flow sees it coming while the passenger is still in the air",
    lead: "Forecasts scored only on days the engine had not seen.",
    ids: ["fixed_rule_caught", "flow_caught_t90", "flow_auc_t90", "day_before_auc"],
  },
  {
    title: "On one real evening, three ways to handle it",
    lead: "The same passengers, replayed under each approach.",
    ids: ["missed_passengers", "today_plan_before_landing", "flow_plan_before_landing", "auto_plan_before_landing",
      "flow_wrong_bumps", "auto_wrong_bumps"],
  },
];

const LABEL_STYLE: Record<string, string> = {
  REAL: "bg-ok-bg text-ok", ASSUMED: "bg-warn text-warn-text",
  SYNTHETIC: "bg-[#ECE8F5] text-[#5B4B8A]", SIMULATED: "bg-info text-deep",
};

function Metric({ metric }: { metric: ImpactMetric }) {
  const highlight = metric.id.startsWith("flow_");
  return (
    <div className={`rounded-[12px] border bg-white p-5 ${highlight ? "border-deep" : "border-line"}`}>
      <div className="text-[34px] font-bold leading-none text-deep">
        {String(metric.value)}<span className="ml-1 text-[16px] font-medium text-muted">{metric.unit}</span>
      </div>
      <div className="mt-2 text-[14px] text-ink">{metric.note}</div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-[12px] text-muted">
        <span className={`rounded px-1 text-[11px] font-bold tracking-wide ${LABEL_STYLE[metric.label] ?? ""}`}>{metric.label}</span>
        {metric.source}
      </div>
    </div>
  );
}

export function ImpactPanel() {
  const [metrics, setMetrics] = useState<ImpactMetric[] | null>(null);
  useEffect(() => {
    api.impact().then(setMetrics).catch(() => setMetrics([]));
  }, []);
  const byId = new Map((metrics ?? []).map((m) => [m.id, m]));
  const extra = (metrics ?? []).filter((m) => !SECTIONS.some((s) => s.ids.includes(m.id)));
  return (
    <div className="min-h-screen bg-staffpage">
      <header className="bg-gradient-to-r from-heroFrom to-heroTo px-8 py-5 text-white">
        <div className="text-[20px] font-bold">Cathay Flow · Impact</div>
        <div className="text-[14px] text-white/90">Evidence from real Hong Kong days. Flights are real; passengers are synthetic.</div>
      </header>
      <main className="mx-auto max-w-[1200px] px-8 py-8">
        {metrics && metrics.length === 0 && (
          <p className="rounded-[12px] border border-line bg-white px-6 py-8 text-center text-muted">
            The evidence has not been built yet.
          </p>
        )}
        {SECTIONS.map((section) => {
          const items = section.ids.map((id) => byId.get(id)).filter((m): m is ImpactMetric => Boolean(m));
          if (!items.length) return null;
          return (
            <section key={section.title} className="mb-8">
              <h2 className="text-[20px] font-bold text-ink">{section.title}</h2>
              <p className="mb-3 text-[14px] text-muted">{section.lead}</p>
              <div className={`grid gap-4 sm:grid-cols-2 ${items.length === 4 ? "lg:grid-cols-4" : "lg:grid-cols-3"}`}>
                {items.map((metric) => <Metric key={metric.id} metric={metric} />)}
              </div>
            </section>
          );
        })}
        {extra.length > 0 && (
          <section className="mb-8">
            <h2 className="mb-3 text-[20px] font-bold text-ink">How the engine is calibrated</h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {extra.map((metric) => <Metric key={metric.id} metric={metric} />)}
            </div>
          </section>
        )}
        <p className="text-[12px] text-muted">
          A connection "breaks" when the real gate-arrival time plus a modelled transfer time is later than the real gate
          close. There are no public passenger outcomes, so transfer times are documented assumptions.
        </p>
      </main>
    </div>
  );
}
