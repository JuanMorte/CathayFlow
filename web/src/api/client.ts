// Typed calls to the backend. Types come from contracts/openapi.json (`make contract`).
import type { components } from "./types";

type S = components["schemas"];
export type ConnectionStatus = S["ConnectionStatus"];
export type Option = S["Option"];
export type Draft = S["Draft"];
export type Trip = S["Trip"];
export type Wave = S["Wave"];
export type WaveSummary = S["WaveSummary"];
export type InboundSummary = S["InboundSummary"];
export type ReplayState = S["ReplayState"];
export type FlightRef = S["FlightRef"];
export type ImpactMetric = S["ImpactMetric"];
export type PlannerOptions = S["PlannerOptions"];
export type PlannerRequest = S["PlannerRequest"];
export type PlannerResult = S["PlannerResult"];

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const reply = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!reply.ok) {
    let detail = reply.statusText;
    try {
      detail = (await reply.json()).detail ?? detail;
    } catch {
      /* keep the status text */
    }
    throw new ApiError(reply.status, String(detail));
  }
  return reply.json() as Promise<T>;
}

const post = <T>(path: string, body: unknown) => call<T>(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  replayState: () => call<ReplayState>("/api/replay/state"),
  control: (action: "play" | "pause" | "seek" | "speed" | "reset", extra: { t?: string; speed?: number } = {}) =>
    post<ReplayState>("/api/replay/control", { action, ...extra }),
  trip: (pid: string) => call<Trip>(`/api/passengers/${pid}/trip`),
  protect: (pid: string) => call<ConnectionStatus>(`/api/passengers/${pid}/protect`),
  options: (pid: string) => call<Option[]>(`/api/passengers/${pid}/options`),
  choose: (pid: string, optionId: string) =>
    post<ConnectionStatus>(`/api/passengers/${pid}/choose`, { option_id: optionId }),
  wave: () => call<Wave>("/api/staff/wave"),
  drafts: (status?: string) => call<Draft[]>(`/api/staff/drafts${status ? `?status=${status}` : ""}`),
  decide: (id: string, decision: "approve" | "reject", note?: string) =>
    post<Draft>(`/api/staff/drafts/${id}`, { decision, note }),
  approveBatch: (ids: string[]) => post<Draft[]>("/api/staff/drafts/approve-batch", { ids }),
  impact: () => call<ImpactMetric[]>("/api/impact"),
  plannerOptions: () => call<PlannerOptions>("/api/planner/options"),
  plan: (request: PlannerRequest) => post<PlannerResult>("/api/planner/plan", request),
};
