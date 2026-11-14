import { BrowserRouter, Link, Navigate, Route, Routes } from "react-router-dom";
import { PassengerApp } from "./app/PassengerApp";
import { ImpactPanel } from "./impact/ImpactPanel";
import { StaffConsole } from "./staff/StaffConsole";

function Index() {
  const links = [
    { to: "/app", title: "Passenger app", detail: "The traveller's phone" },
    { to: "/staff", title: "Flow Ops", detail: "Staff console and replay controls" },
    { to: "/impact", title: "Impact", detail: "Evidence from real Hong Kong days" },
  ];
  return (
    <div className="mx-auto max-w-[520px] px-4 py-12">
      <h1 className="text-[28px] font-bold text-deep">Cathay Flow</h1>
      <p className="mt-1 text-muted">Connection Protect for transfer passengers at Hong Kong.</p>
      <div className="mt-6 flex flex-col gap-3">
        {links.map((link) => (
          <Link key={link.to} to={link.to} className="rounded-[12px] border border-line bg-white px-5 py-4 hover:bg-info">
            <div className="font-bold text-ink">{link.title}</div>
            <div className="text-[14px] text-muted">{link.detail}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Index />} />
        <Route path="/app" element={<PassengerApp />} />
        <Route path="/staff" element={<StaffConsole />} />
        <Route path="/impact" element={<ImpactPanel />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
