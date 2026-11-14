// Building blocks of the passenger app, after the Figma frames (393 × 852). The top bar and the bottom
// navigation stay fixed; only the middle scrolls.
import type { ReactNode } from "react";
import backSvg from "../../assets/flow/svg/back.svg?raw";
import navBook from "../../assets/flow/svg/nav-book.svg?raw";
import navHome from "../../assets/flow/svg/nav-home.svg?raw";
import navProfile from "../../assets/flow/svg/nav-profile.svg?raw";
import navTools from "../../assets/flow/svg/nav-tools.svg?raw";
import navTrips from "../../assets/flow/svg/nav-trips.svg?raw";
import external from "../../assets/flow/icon-external.png";
import upArrow from "../../assets/flow/icon-up.png";

/** An SVG from the design, recoloured to the text colour. */
export function Svg({ src, className = "", keepFill = false }: { src: string; className?: string; keepFill?: boolean }) {
  let markup = src.replace(/stroke="#(616163|367877|151515)"/g, 'stroke="currentColor"');
  if (!keepFill) markup = markup.replace(/fill="#(616163|367877|151515)"/g, 'fill="currentColor"');
  markup = markup.replace(/ style="display: block;"/, "").replace(/width="[\d.]+" height="[\d.]+"/, 'width="100%" height="100%"');
  return <span className={`inline-block ${className}`} dangerouslySetInnerHTML={{ __html: markup }} />;
}

export function PhoneFrame({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[#E7EEEE] font-jost sm:flex sm:items-center sm:justify-center sm:py-6">
      <div className="relative mx-auto flex h-[100dvh] w-full max-w-[430px] flex-col overflow-hidden bg-page sm:h-[852px] sm:w-[393px] sm:rounded-[44px] sm:border-[10px] sm:border-[#1D1D1F] sm:shadow-2xl">
        {children}
      </div>
    </div>
  );
}

/** The phone's own status bar, drawn only in the laptop frame. */
export function StatusBar({ time, light = false }: { time: string; light?: boolean }) {
  return (
    <div className={`relative z-10 hidden h-[54px] shrink-0 items-center justify-between px-[46px] pt-1 sm:flex ${light ? "text-white" : "text-black"}`}>
      <span className="font-sans text-[17px] font-semibold">{time}</span>
      <span className="flex items-center gap-[6px]">
        <svg viewBox="0 0 18 12" className="h-[12px] w-[19px]" fill="currentColor" aria-hidden="true">
          <rect x="0" y="8" width="3" height="4" rx="1" /><rect x="5" y="5.5" width="3" height="6.5" rx="1" />
          <rect x="10" y="3" width="3" height="9" rx="1" /><rect x="15" y="0" width="3" height="12" rx="1" />
        </svg>
        <svg viewBox="0 0 16 12" className="h-[12px] w-[17px]" fill="currentColor" aria-hidden="true">
          <path d="M8 2.2c2.4 0 4.6.9 6.2 2.5l1.2-1.2A10.4 10.4 0 0 0 8 .5 10.4 10.4 0 0 0 .6 3.5l1.2 1.2A8.7 8.7 0 0 1 8 2.2zm0 3.4c1.5 0 2.8.6 3.8 1.5L13 5.9A7 7 0 0 0 8 3.9a7 7 0 0 0-5 2l1.2 1.2c1-.9 2.3-1.5 3.8-1.5zM8 9l1.9 1.9L8 12.8 6.1 10.9z" />
        </svg>
        <span className="flex h-[13px] w-[27px] items-center rounded-[4px] border border-current/40 p-[2px]">
          <span className="h-full w-full rounded-[2px] bg-current" />
        </span>
      </span>
    </div>
  );
}

/** White bar: back arrow and "Cathay Flow". Fixed at the top. */
export function TopBar({ time, title = "Cathay Flow", onBack }: { time: string; title?: string; onBack?: () => void }) {
  return (
    <div className="relative z-20 shrink-0 border-b border-[#E6E6E6] bg-white">
      <StatusBar time={time} />
      <div className="relative flex h-[50px] items-center justify-center pt-2 sm:h-[50px]">
        <button onClick={onBack} aria-label="Back" className="absolute left-[18px] flex h-9 w-9 items-center justify-center text-[#151515]">
          <Svg src={backSvg} className="h-[17px] w-[10px]" />
        </button>
        <span className="text-[19px] text-[#151515]">{title}</span>
      </div>
    </div>
  );
}

/** A photo band under the top bar with a small label and a white title; the route card overlaps its foot. */
export function PhotoHeader({ photo, label, title, height = 194 }: { photo: string; label: string; title: ReactNode; height?: number }) {
  return (
    <div className="relative w-full overflow-hidden" style={{ height }}>
      <img src={photo} alt="" className="absolute inset-0 h-full w-full object-cover" />
      <div className="absolute inset-0 bg-gradient-to-b from-black/45 via-black/20 to-black/10" />
      <div className="relative px-4 pt-[28px] text-white">
        <div className="text-[13px]">{label}</div>
        <div className="mt-[6px] text-[20px] font-bold leading-tight">{title}</div>
      </div>
    </div>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-[15px] bg-white shadow-[0_0_20px_rgba(0,0,0,0.05)] ${className}`}>{children}</div>;
}

/** "Home to CGK": bold teal words around a plain "to". */
export function Route({ from, to, size = 18 }: { from: string; to: string; size?: number }) {
  return (
    <div className="leading-tight" style={{ fontSize: size }}>
      <span className="font-bold text-primary">{from}</span> <span className="text-black">to</span>{" "}
      <span className="font-bold text-primary">{to}</span>
    </div>
  );
}

/** The card that sits on the photo: date, route, and a from → to line with times. */
export function RouteCard({ date, extra, from, to, left, right, middle, icon, midTime, leftTime, rightTime, plus,
  leftNote, rightNote, line = "start" }: {
  date: string; extra?: string; from: string; to: string; left: string; right: string; middle?: string;
  icon: ReactNode; midTime?: string; leftTime: string; rightTime: string; plus?: string; leftNote?: ReactNode;
  rightNote?: ReactNode; line?: "start" | "end";
}) {
  return (
    <Card className="relative z-10 mx-4 -mt-[103px] px-4 pb-4 pt-[17px]">
      <div className="flex items-center text-[12.5px] font-light text-ink">
        <span>{date}</span>
        {extra && <><span className="mx-[9px] h-[14px] w-px bg-[#BDBDBD]" /><span>{extra}</span></>}
      </div>
      <div className="mt-[7px]"><Route from={from} to={to} /></div>
      <div className="mt-[12px] flex min-h-[18px] items-start justify-between">
        <span className="text-[15px] font-bold text-primary">{left}</span>
        <span className="text-[15px] font-bold text-primary">{right}</span>
      </div>
      <div className="relative mt-[2px] flex items-center">
        <span className="w-[86px] shrink-0 text-[23px] leading-none text-black">{leftTime}</span>
        <div className="relative mx-1 h-[40px] flex-1">
          {middle && <div className="absolute -top-[16px] left-0 right-0 text-center text-[12.5px] font-light text-black">{middle}</div>}
          <div className={`absolute top-1/2 left-0 right-0 h-px ${line === "end" ? "bg-black" : "bg-[#D9D9D9]"}`} />
          <span className={`absolute top-1/2 -translate-y-1/2 ${line === "end" ? "right-0" : "left-0"}`}>{icon}</span>
          {line === "start" && <span className="absolute right-0 top-1/2 h-[8px] w-[8px] -translate-y-1/2 rounded-full bg-[#D9D9D9]" />}
          {line === "end" && <span className="absolute left-0 top-1/2 h-[8px] w-[8px] -translate-y-1/2 rounded-full bg-black" />}
          {midTime && (
            <>
              <span className="absolute left-1/2 top-1/2 h-[10px] w-[10px] -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-primary bg-white" />
              <span className="absolute left-1/2 top-[27px] -translate-x-1/2 text-[13px] text-black">{midTime}</span>
            </>
          )}
        </div>
        <span className="relative w-[86px] shrink-0 text-right text-[23px] leading-none text-black">
          {plus && <span className="absolute -left-[4px] -top-[8px] font-jost text-[11px] font-bold text-late">{plus}</span>}
          {rightTime}
        </span>
      </div>
      <div className="mt-[4px] flex justify-between text-[11px] font-light leading-tight text-black">
        <span className="max-w-[120px]">{leftNote}</span>
        <span className="max-w-[140px] text-right">{rightNote}</span>
      </div>
    </Card>
  );
}

export function Section({ title, action, onAction, children }: { title: string; action?: string; onAction?: () => void; children: ReactNode }) {
  return (
    <section className="mx-4 mt-[26px]">
      <div className="mb-[14px] flex items-baseline justify-between px-[3px]">
        <h2 className="text-[22px] text-black">{title}</h2>
        {action && <button onClick={onAction} className="text-[15px] text-primary">{action}</button>}
      </div>
      {children}
    </section>
  );
}

export type JourneyRow = { icon: string; title: string; detail: string; time: string };

/** Checkpoints: round icons joined by a line; the first `done` are filled teal. */
export function Journey({ rows, done = 0 }: { rows: JourneyRow[]; done?: number }) {
  return (
    <Card className="px-[10px] py-[12px]">
      <ol>
        {rows.map((row, index) => {
          const filled = index < done;
          return (
            <li key={row.title} className="relative flex items-center gap-[14px] py-[12px]">
              {index < rows.length - 1 && (
                <span className={`absolute left-[17px] top-[44px] h-[calc(100%-32px)] w-[4px] ${index < done - 1 || (filled && index === done - 1) ? "bg-primary" : "bg-[#F1F1F1]"}`} />
              )}
              <span className={`relative flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-full ${filled ? "bg-primary" : "bg-[#F1F1F1]"}`}>
                <img src={row.icon} alt="" className={`h-[16px] w-[16px] object-contain ${filled ? "brightness-0 invert" : ""}`} />
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-[15.5px] font-bold leading-tight text-black">{row.title}</div>
                <div className="mt-[3px] font-sans text-[12px] text-muted">{row.detail}</div>
              </div>
              <span className="pr-[6px] text-[15px] font-medium text-primary">{row.time}</span>
            </li>
          );
        })}
      </ol>
    </Card>
  );
}

/** "Open Gojek for taxi" with the app's logo and an external-link mark. */
export function AppLink({ logo, app, rest, wide = false }: { logo: string; app: string; rest: string; wide?: boolean }) {
  return (
    <a href="#" onClick={(e) => e.preventDefault()}
      className="mb-[12px] flex min-h-[53px] items-center gap-[14px] rounded-[10px] bg-white px-[12px] shadow-[0_0_20px_rgba(0,0,0,0.05)]">
      <img src={logo} alt="" className={`${wide ? "w-[38px]" : "w-[30px]"} h-[30px] shrink-0 object-contain`} />
      <span className="flex-1 font-sans text-[14px] text-black">Open <b>{app}</b> {rest}</span>
      <img src={external} alt="" className="h-[18px] w-[18px]" />
    </a>
  );
}

/** Next instruction, with a picture or map underneath. */
export function NavGuide({ title, detail, image, footer }: { title: string; detail: string; image: string; footer?: ReactNode }) {
  return (
    <Card className="overflow-hidden">
      <div className="flex items-center gap-[13px] px-[8px] py-[6px]">
        <img src={upArrow} alt="" className="h-[40px] w-[40px]" />
        <div>
          <div className="font-sans text-[13px] font-bold text-black">{title}</div>
          <div className="font-sans text-[10.5px] text-muted">{detail}</div>
        </div>
      </div>
      <img src={image} alt="" className="block h-[202px] w-full object-cover" />
      {footer}
    </Card>
  );
}

export function Notice({ icon, title, children }: { icon: string; title: string; children?: ReactNode }) {
  return (
    <div className="mx-4 mt-[16px] flex gap-[10px] rounded-[5px] bg-warn px-[10px] py-[8px]">
      <img src={icon} alt="" className="mt-[1px] h-[16px] w-[16px] shrink-0" />
      <div>
        <div className="text-[13px] font-bold text-black">{title}</div>
        {children && <div className="text-[10px] font-light leading-snug text-black">{children}</div>}
      </div>
    </div>
  );
}

export function BottomNav({ active, onHome, onTrips, onTools }: {
  active: "home" | "trips" | "tools"; onHome: () => void; onTrips: () => void; onTools: () => void;
}) {
  const items = [
    { key: "home", label: "Home", svg: navHome, onClick: onHome },
    { key: "book", label: "Book", svg: navBook },
    { key: "trips", label: "My trips", svg: navTrips, onClick: onTrips },
    { key: "profile", label: "Profile", svg: navProfile },
    { key: "tools", label: "Travel tools", svg: navTools, onClick: onTools },
  ];
  return (
    <nav className="relative z-20 shrink-0 border-t border-[#E6E6E6] bg-white font-figtree">
      <div className="flex pt-[12px]">
        {items.map((item) => {
          const on = active === item.key;
          return (
            <button key={item.key} onClick={item.onClick} disabled={!item.onClick}
              className={`flex flex-1 flex-col items-center gap-[4px] text-[11px] ${on ? "font-bold text-primary" : "text-nav"}`}>
              <Svg src={item.key === "trips" && !on ? item.svg.replace(/fill="#367877"/, 'fill="none"') : item.svg}
                keepFill={item.key === "trips"} className={`h-[20px] w-[20px] ${item.key === "trips" && !on ? "text-nav" : ""}`} />
              {item.label}
            </button>
          );
        })}
      </div>
      <div className="flex justify-center pb-[8px] pt-[16px]">
        <span className="hidden h-[5px] w-[134px] rounded-full bg-black sm:block" />
      </div>
    </nav>
  );
}
