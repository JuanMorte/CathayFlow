// Shared building blocks of the passenger app, after docs/design/ (phone frames 393 × 852).
import type { ReactNode } from "react";

export function PhoneFrame({ children }: { children: ReactNode }) {
  // Full screen on a phone; a phone-sized frame on a laptop.
  return (
    <div className="min-h-screen bg-[#E7EEEE] sm:flex sm:items-center sm:justify-center sm:py-6">
      <div className="relative mx-auto flex h-[100dvh] w-full max-w-[430px] flex-col overflow-hidden bg-page sm:h-[852px] sm:w-[393px] sm:rounded-[44px] sm:border-[10px] sm:border-[#1D1D1F] sm:shadow-2xl">
        {children}
      </div>
    </div>
  );
}

/** The phone's own status bar, drawn only in the laptop frame (a real phone has its own). */
export function StatusBar({ time, dark = false, carrier }: { time: string; dark?: boolean; carrier?: string }) {
  const colour = dark ? "text-white" : "text-ink";
  return (
    <div className={`relative z-10 hidden h-[44px] shrink-0 items-center justify-between px-7 sm:flex ${colour}`}>
      <span className="text-[16px] font-semibold">{carrier ?? time}</span>
      <span className="flex items-center gap-[6px]">
        <svg viewBox="0 0 18 12" className="h-[11px] w-[18px]" fill="currentColor" aria-hidden="true">
          <rect x="0" y="8" width="3" height="4" rx="1" /><rect x="5" y="5.5" width="3" height="6.5" rx="1" />
          <rect x="10" y="3" width="3" height="9" rx="1" /><rect x="15" y="0" width="3" height="12" rx="1" />
        </svg>
        <svg viewBox="0 0 16 12" className="h-[11px] w-[16px]" fill="currentColor" aria-hidden="true">
          <path d="M8 2.2c2.4 0 4.6.9 6.2 2.5l1.2-1.2A10.4 10.4 0 0 0 8 .5 10.4 10.4 0 0 0 .6 3.5l1.2 1.2A8.7 8.7 0 0 1 8 2.2zm0 3.4c1.5 0 2.8.6 3.8 1.5L13 5.9A7 7 0 0 0 8 3.9a7 7 0 0 0-5 2l1.2 1.2c1-.9 2.3-1.5 3.8-1.5zM8 9l1.9 1.9L8 12.8 6.1 10.9z" />
        </svg>
        <span className="flex h-[12px] w-[25px] items-center rounded-[4px] border border-current p-[1.5px] opacity-90">
          <span className="h-full w-[75%] rounded-[2px] bg-current" />
        </span>
      </span>
    </div>
  );
}

export function Icon({ name, className = "" }: { name: string; className?: string }) {
  const paths: Record<string, ReactNode> = {
    back: <path d="M15 5l-7 7 7 7" />,
    close: <path d="M6 6l12 12M18 6L6 18" />,
    more: (
      <>
        <circle cx="5" cy="12" r="1.5" fill="currentColor" stroke="none" />
        <circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none" />
        <circle cx="19" cy="12" r="1.5" fill="currentColor" stroke="none" />
      </>
    ),
    plane: <path d="M21 15.5v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V8.5l-8 5v2l8-2.5V18l-2 1.5V21l3.5-1 3.5 1v-1.5L13 18v-5l8 2.5z" fill="currentColor" stroke="none" />,
    home: <path d="M4 11l8-7 8 7v9h-5v-6H9v6H4z" />,
    book: <path d="M21 15.5v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V8.5l-8 5v2l8-2.5V18l-2 1.5V21l3.5-1 3.5 1v-1.5L13 18v-5l8 2.5z" />,
    trips: <path d="M5 8h14v11H5zM9 8V5h6v3M9 8v11M15 8v11" />,
    profile: <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-7 9a7 7 0 0 1 14 0" />,
    tools: <path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z" />,
    bell: <path d="M6 16V11a6 6 0 1 1 12 0v5l2 2H4zM10 20a2 2 0 0 0 4 0" />,
    bag: <path d="M7 7h10v13H7zM9.5 7V4h5v3M7 12h10M9 20v1M15 20v1" />,
    info: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 11v5M12 8v.5" />
      </>
    ),
    check: <path d="M5 12l5 5 9-10" />,
    chevron: <path d="M9 5l7 7-7 7" />,
    seat: <path d="M7 4v9h9l2 7M7 13l-2 7M10 17h6" />,
    cup: <path d="M5 9h11v5a5 5 0 0 1-10 0zM16 10h2a2 2 0 0 1 0 4h-2M8 3v3M12 3v3" />,
    flow: <path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8" />,
    lock: <path d="M7 11V8a5 5 0 0 1 10 0v3M6 11h12v9H6z" />,
    doc: <path d="M7 3h7l4 4v14H7zM14 3v4h4M10 12h5M10 16h5" />,
    people: <path d="M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM3 20a6 6 0 0 1 12 0M16 4.5a3.5 3.5 0 0 1 0 6.5M18 14a5.5 5.5 0 0 1 3 6" />,
    walk: <path d="M13 4.5a1.5 1.5 0 1 0 0-.01M10 21l2-6 3 3v3M9 9l3-2 3 4 3 1M12 7l-1 6" />,
    shield: <path d="M12 3l7 3v6c0 4-3 7.5-7 9-4-1.5-7-5-7-9V6zM9 12l2 2 4-4" />,
    car: <path d="M5 16V12l2-5h10l2 5v4M5 16h14M5 16v2M19 16v2M7.5 13.5h.5M16 13.5h.5" />,
    taxi: <path d="M5 16V12l2-5h10l2 5v4M5 16h14M5 16v2M19 16v2M10 7V5h4v2" />,
    train: <path d="M7 4h10v12H7zM7 11h10M9 20l1-4M15 20l-1-4M9.5 13.5h.5M14 13.5h.5" />,
    map: <path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2zM9 4v14M15 6v14" />,
    exit: <path d="M14 4h5v16h-5M10 8l-4 4 4 4M6 12h9" />,
    pen: <path d="M4 20l4-1 11-11-3-3L5 16zM14 6l3 3" />,
    torch: <path d="M9 3h6v4l-2 4v9h-2v-9L9 7zM9 7h6" />,
    camera: <path d="M4 8h4l2-2h4l2 2h4v11H4zM12 16.5a3 3 0 1 0 0-6 3 3 0 0 0 0 6z" />,
    toggle: <path d="M7 7h10a5 5 0 0 1 0 10H7A5 5 0 0 1 7 7z" />,
  };
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"
      strokeLinejoin="round" className={className} aria-hidden="true">
      {paths[name]}
    </svg>
  );
}

/** Cathay-style brushwing mark, drawn as a simple swoosh (no image asset). */
export function Brushwing({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 28" className={className} fill="currentColor" aria-hidden="true">
      <path d="M2 18c9-1 17-6 24-15 2-2 4-2 3 1-3 7-9 13-17 16 7 0 13-2 19-6 2-1 4 0 2 2-6 6-15 9-25 9-4 0-7-2-6-7z" />
    </svg>
  );
}

/** Mint header with the soft circle, title, subtitle and menu; the journey strip sits inside it. */
export function Header({ time, title, subtitle, onBack, onMenu, close, right, children }: {
  time: string; title: string; subtitle?: string; onBack?: () => void; onMenu?: () => void;
  close?: boolean; right?: ReactNode; children?: ReactNode;
}) {
  return (
    <div className="relative shrink-0 overflow-hidden bg-mint pb-6">
      <div className="pointer-events-none absolute -right-24 -top-28 h-[300px] w-[300px] rounded-full bg-white/35" />
      <StatusBar time={time} />
      <div className="relative flex items-center px-3 pt-2 sm:pt-0">
        <button onClick={onBack} aria-label={close ? "Close" : "Back"}
          className="flex h-9 w-9 items-center justify-center rounded-full text-ink focus-visible:ring-2 focus-visible:ring-primary">
          <Icon name={close ? "close" : "back"} className="h-[22px] w-[22px]" />
        </button>
        <div className="flex-1 text-center">
          <div className="text-[17px] font-bold leading-tight text-ink">{title}</div>
          {subtitle && <div className="mt-[2px] text-[12.5px] text-muted">{subtitle}</div>}
        </div>
        {right ?? (
          <button onClick={onMenu} aria-label="More"
            className="flex h-9 w-9 items-center justify-center rounded-full text-ink focus-visible:ring-2 focus-visible:ring-primary">
            <Icon name="more" className="h-[22px] w-[22px]" />
          </button>
        )}
      </div>
      {children}
    </div>
  );
}

export type Stop = { code: string; time: string; late?: boolean; onTap?: () => void };

/**
 * Home → origin → HKG → destination → Exit. The first `done` stops are ticked, `here` is ringed,
 * and the line is dark up to `progress` (in stops: 1.5 = halfway from the second to the third),
 * where the plane sits while flying.
 */
export function JourneyStrip({ stops, done, here, progress, flying }: {
  stops: Stop[]; done: number; here: number | null; progress: number; flying: boolean;
}) {
  const span = stops.length - 1;
  const pct = (value: number) => `${(Math.min(Math.max(value, 0), span) / span) * 100}%`;
  return (
    <div className="relative px-[30px] pt-3">
      <div className="relative h-[18px]">
        <div className="absolute left-0 right-0 top-[8px] h-[2px] bg-[#A9C6C5]" />
        <div className="absolute left-0 top-[7px] h-[3px] bg-deep" style={{ width: pct(progress) }} />
        {flying && (
          <span className="absolute top-[-1px] -translate-x-1/2 text-deep" style={{ left: pct(progress) }}>
            <Icon name="plane" className="h-[20px] w-[20px] rotate-90" />
          </span>
        )}
        {stops.map((stop, index) => {
          const isHere = index === here;
          const isDone = index < done;
          return (
            <button key={stop.code + index} onClick={stop.onTap} disabled={!stop.onTap} aria-label={stop.code}
              className="absolute top-0 -translate-x-1/2 focus-visible:outline-none" style={{ left: pct(index) }}>
              {isHere ? (
                <span className="flex h-[20px] w-[20px] items-center justify-center rounded-full border-[2px] border-deep bg-white">
                  <span className="h-[9px] w-[9px] rounded-full bg-deep" />
                </span>
              ) : isDone ? (
                <span className="flex h-[18px] w-[18px] items-center justify-center rounded-full bg-deep text-white">
                  <Icon name="check" className="h-[11px] w-[11px]" />
                </span>
              ) : (
                <span className="block h-[18px] w-[18px] rounded-full border-[2px] border-[#A9C6C5] bg-white" />
              )}
            </button>
          );
        })}
      </div>
      <div className="relative mt-[6px] h-[34px]">
        {stops.map((stop, index) => (
          <button key={stop.code + index} onClick={stop.onTap} disabled={!stop.onTap}
            className="absolute top-0 w-16 -translate-x-1/2 text-center" style={{ left: pct(index) }}>
            <div className="text-[13px] font-bold leading-tight text-deep">{stop.code}</div>
            <div className={`text-[12px] leading-tight ${stop.late ? "font-bold text-late" : "text-ink"}`}>{stop.time}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

export function HeroCard({ tag, children }: { tag: string; children: ReactNode }) {
  return (
    <div className="relative z-10 mx-4 -mt-[18px] overflow-hidden rounded-[14px] bg-gradient-to-br from-heroFrom to-heroTo px-4 pb-4 pt-[14px] text-white">
      <svg className="pointer-events-none absolute right-0 top-0 h-full w-[60%] opacity-[0.12]" viewBox="0 0 100 100" preserveAspectRatio="none">
        <path d="M100 5 C 70 25, 75 60, 30 100" stroke="white" fill="none" strokeWidth="0.5" />
        <path d="M100 25 C 78 40, 85 75, 50 100" stroke="white" fill="none" strokeWidth="0.5" />
        <path d="M100 45 C 88 60, 92 85, 70 100" stroke="white" fill="none" strokeWidth="0.5" />
      </svg>
      <span className="inline-block rounded-full bg-white px-[10px] py-[3px] text-[10.5px] font-bold uppercase tracking-[0.06em] text-deep">{tag}</span>
      <div className="relative mt-2">{children}</div>
    </div>
  );
}

/** Three figures in a row under a divider, as on the Navigate hero. */
export function HeroStats({ items }: { items: { label: string; value: string }[] }) {
  return (
    <div className="mt-4 flex border-t border-white/25 pt-2">
      {items.map((item, index) => (
        <div key={item.label} className={`flex-1 ${index ? "border-l border-white/25 pl-3" : ""}`}>
          <div className="text-[13px] text-white/90">{item.label}</div>
          <div className="text-[19px] font-bold">{item.value}</div>
        </div>
      ))}
    </div>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-[12px] border border-line bg-white ${className}`}>{children}</div>;
}

export function Tag({ tone, caps = true, children }: { tone: "mint" | "sand" | "ok" | "late"; caps?: boolean; children: ReactNode }) {
  const style = {
    mint: "bg-planA-bg text-planA-text", sand: "bg-planB-bg text-planB-text",
    ok: "bg-ok-bg text-ok", late: "bg-[#FBE7DA] text-late",
  }[tone];
  const text = caps ? "text-[11px] uppercase tracking-[0.04em]" : "text-[12.5px]";
  return <span className={`whitespace-nowrap rounded-full px-[10px] py-[3px] font-bold ${text} ${style}`}>{children}</span>;
}

export function Notice({ kind = "info", icon, children, onClick }: {
  kind?: "info" | "warn"; icon: string; children: ReactNode; onClick?: () => void;
}) {
  const style = kind === "warn" ? "bg-warn text-warn-text" : "bg-info text-ink";
  return (
    <div onClick={onClick} role={onClick ? "button" : undefined}
      className={`flex items-start gap-[10px] rounded-[10px] px-3 py-[10px] text-[13.5px] leading-snug ${style} ${onClick ? "cursor-pointer" : ""}`}>
      <Icon name={icon} className="mt-[1px] h-[18px] w-[18px] shrink-0" />
      <div>{children}</div>
    </div>
  );
}

export type Step = { title: string; detail?: string; state: "done" | "now" | "next"; time?: string; extra?: ReactNode };

/** Vertical checkpoints: filled = done, ringed = now, hollow = next; dashed line ahead. */
export function Timeline({ steps, timeColumn = false }: { steps: Step[]; timeColumn?: boolean }) {
  return (
    <ol className="flex flex-col">
      {steps.map((step, index) => {
        const last = index === steps.length - 1;
        const nextDone = steps[index + 1]?.state !== "next";
        return (
          <li key={step.title + index} className="relative flex gap-3 pb-[14px] last:pb-0">
            {timeColumn && <span className="w-[46px] shrink-0 pt-[1px] text-[15px] font-bold text-deep">{step.time}</span>}
            <span className="relative flex w-[20px] shrink-0 justify-center">
              {!last && (
                <span className={`absolute top-[20px] h-[calc(100%-6px)] ${nextDone ? "w-[2px] bg-deep" : "w-0 border-l-2 border-dashed border-[#A9C6C5]"}`} />
              )}
              {step.state === "done" ? (
                <span className="relative mt-[1px] flex h-[19px] w-[19px] items-center justify-center rounded-full bg-deep text-white">
                  <Icon name="check" className="h-[11px] w-[11px]" />
                </span>
              ) : step.state === "now" ? (
                <span className="relative mt-[1px] flex h-[20px] w-[20px] items-center justify-center rounded-full border-2 border-deep bg-white">
                  <span className="h-[9px] w-[9px] rounded-full bg-deep" />
                </span>
              ) : (
                <span className="relative mt-[2px] block h-[17px] w-[17px] rounded-full border-[1.5px] border-[#8FB1B0] bg-white" />
              )}
            </span>
            <div className="min-w-0 flex-1">
              <div className="text-[15px] font-bold leading-tight text-ink">{step.title}</div>
              {step.detail && <div className="mt-[2px] text-[13px] text-muted">{step.detail}</div>}
              {step.extra}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export function PrimaryButton({ children, onClick, disabled, icon }: {
  children: ReactNode; onClick?: () => void; disabled?: boolean; icon?: string;
}) {
  return (
    <button onClick={onClick} disabled={disabled}
      className="flex min-h-[50px] flex-1 items-center justify-center gap-2 rounded-[8px] bg-button px-3 text-[15.5px] font-medium text-white disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
      {icon && <Icon name={icon} className="h-5 w-5" />}
      {children}
    </button>
  );
}

export function SecondaryButton({ children, onClick, disabled }: { children: ReactNode; onClick?: () => void; disabled?: boolean }) {
  return (
    <button onClick={onClick} disabled={disabled}
      className="min-h-[50px] flex-1 rounded-[8px] border-[1.5px] border-primary bg-white px-3 text-[15.5px] font-medium text-primary disabled:border-line disabled:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
      {children}
    </button>
  );
}

export function BottomNav({ active, onHome, onTrips, onTools }: {
  active: "home" | "trips" | "tools"; onHome?: () => void; onTrips?: () => void; onTools?: () => void;
}) {
  const items = [
    { key: "home", label: "Home", icon: "home", onClick: onHome },
    { key: "book", label: "Book", icon: "book" },
    { key: "trips", label: "My trips", icon: "trips", onClick: onTrips },
    { key: "profile", label: "Profile", icon: "profile" },
    { key: "tools", label: "Travel tools", icon: "tools", onClick: onTools },
  ];
  return (
    <nav className="mt-auto shrink-0 border-t border-line bg-white">
      <div className="flex pt-[6px]">
        {items.map((item) => (
          <button key={item.key} onClick={item.onClick} disabled={!item.onClick}
            className={`flex flex-1 flex-col items-center pb-1 text-[11.5px] ${active === item.key ? "font-bold text-primary" : "text-nav"}`}>
            <Icon name={item.icon} className="mb-[3px] h-[24px] w-[24px]" />
            {item.label}
          </button>
        ))}
      </div>
      <div className="flex justify-center pb-2 pt-[10px]">
        <span className="hidden h-[5px] w-[134px] rounded-full bg-ink sm:block" />
      </div>
    </nav>
  );
}

export function SampleNote() {
  return (
    <p className="px-4 pb-3 pt-2 text-center text-[11px] text-muted">
      Flights and times are real. Passenger details and some trip details are sample data.
    </p>
  );
}
