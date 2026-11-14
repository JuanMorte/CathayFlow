# Demo script (2 minutes)

Written for the presenter. Every number below comes from the running app or `data/evidence.json` (built
2026-11-14). If the scenario or evidence is rebuilt, re-check them on screen before going on stage.

**Setup (before going on stage)**
- **Laptop:** `/staff` on the AppUrl, or with Wi-Fi off `OFFLINE=1 make demo` → http://localhost:8000/staff.
- **Phone:** `/app`. It opens as Mei. On a laptop, the same page shows a framed phone.
- **Start state:** in the staff console press **Start of day** (05:30 HKT); keep the replay paused until you start
  talking. Open the phone on **Cathay Flow is on** → it shows "Your Melbourne connection looks good".
- **Second laptop tab:** `/impact`.
- **Never deploy during the demo.**

**1. The passenger (0:00–0:20)**

"Mei is flying Business on CX254 from London, a real Cathay flight on Thursday 22 October 2026, connecting in
Hong Kong to CX135 to Melbourne, 60 minutes later. Mei is synthetic; the flights and times are real."

**2. The slip, then in the air (0:20–0:45)**

- **Press Play** in the staff console. At 05:37 Hong Kong time (about seven seconds in) CX254 pushes back in London
  13 minutes late, and the phone turns from "looks good" to **"Your Melbourne connection is tight"**.
- **Press Before landing.**
- **The phone shows:**
  - CX254 now lands 18:21 (21 min late); the gate for CX135 closes at 18:45.
  - **Both seats are held for you:** CX135 at 19:00 *Original · still held*, and CX105 at 00:20 *If you miss it*,
    landing Melbourne 12:15 Friday.
- **Optional:** ⋯ → *Preview lock-screen alert*.

**3. Staff console (0:45–1:10)**

- **On screen:** the CX254 card shows +21 min and 23 passengers at risk on that flight. Mei's row is pinned at the
  top: 42% miss risk, backup CX105 00:20.
- **Say:** "The engine drafted these; a human approves."
- **Click Approve all.**

**4. Choose before you land (1:10–1:35)**

- **Phone:** the lock-screen alert *"Your options are ready"* appears. Tap it; **Switch to CX105** is now unlocked.
- **Tap it**, then **Confirm switch**. The phone shows *Board CX105 in … hour(s)*.
- **Staff row:** flips to **✓ Rebooked on CX105** within a second.

**5. Impact (1:35–2:00)** — `/impact`

- **Breaks:** "On real days, 11.5% of tight Cathay connections break, 19.5% on disrupted days, and the next flight
  is a median 8.6 hours away."
- **Spotting them:** "A fixed 38-minute rule catches none of them. Flow, 90 minutes before landing, catches 93% while
  flagging 22% of tight connections."
- **That evening:** "Of 145 passengers who missed, Flow gave 94 an approved plan before landing, with zero wrong
  bumps. An auto-rebook rule would have planned for 75 and moved 23 people off flights they would have made."

**If asked**

- **Is this real?**
  - **Flights:** times, stands and gates are HKIA public data.
  - **In-flight estimates:** OAG.
  - **Passengers:** synthetic, sized as seats × Cathay's 87.2% load factor × HKIA's 28% transfer share.
  - **Transfer times:** documented assumptions.
  - **Passenger app:** some details are sample data (README).
- **How do you know it works?** We backtested it on 91 real days and scored it only on days it hadn't seen.
  OAG's in-flight estimates are off by about 11 minutes, and the engine uses that measured error.
- **Free seats?** Seats per cabin × (1 − 87.2%), the seats left unsold on average. With Cathay's inventory it
  would use the real number.
- **What if staff reject?** The backup stays held; nothing changes for the passenger until they choose.
- **What if every later flight is full?** The console flags the passenger "Needs manual rebooking".
- **What about passengers starting in Hong Kong?** Phone → *Travel tools* → Gate Planner. Pick a flight, e.g. CX135.
  It shows when to leave, built from Google traffic, check-in queues, immigration and the walk to the gate, and it
  re-plans when the gate is published or the flight is delayed.
