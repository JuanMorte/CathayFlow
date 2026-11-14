# Demo script (2 minutes)

Written for the presenter. The story is a scripted scenario (`data/scenarios/2026-12-15-jakarta`) run live by the
engine: the flight numbers are Cathay's, the times follow the design. The evidence on `/impact` comes from 91 real
days and the real 22 October replay.

**Setup (before going on stage)**
- **Laptop:** `/staff` on the AppUrl, or with Wi-Fi off `OFFLINE=1 make demo` → http://localhost:8000/staff.
- **Phone:** `/app`. It opens as Ms Wijaya.
- **Start state:** in the "Demo replay" strip press **Start of day** (14 Dec, 21:30 in Jakarta). The phone shows
  "Leave home at 05:10 tomorrow".
- **Never deploy during the demo.**

**1. Before the trip (0:00–0:30)**
- **Phone, Home:** Jakarta to London via Hong Kong, CX718 then CX251, "Cathay Flow is on".
- **Demo replay → Leave home**, then **At the airport**: My trips shows when to leave, check-in, security, the
  walk to the gate.

**2. The delay (0:30–1:00)**
- **Demo replay → Decision time** (13:46 HKT). Flow Ops: CX718 left Jakarta 95 minutes late. Five passengers at
  risk; other agents already rebooked two and kept one. Two wait for this agent.
- **Say:** "The engine drafted these from the live delay; an agent decides."
- **Click Rebook** on Wijaya.

**3. The passenger (1:00–1:30)**
- **Phone:** lock screen "Your connection has changed … moved you and Kai to CX255 tonight". Tap it.
- **Rebooked screen:** CX255 23:55, seats together, bags moved, "Rebooked by a Cathay agent at 13:46", hotline.
- **Say:** "Her CX251 seat is still held until its gate closes. If she makes it after all, she flies it."

**4. After (1:30–1:45)** — **Landed**, then **Arrived**: inside HKIA (gate, time to relax), bags, London arrival.

**5. Impact (1:45–2:00)** — `/impact`: the real-day evidence (93% of breaks caught 90 minutes out, 0 wrong bumps).

**If asked**
- **Is this real?** The story is scripted to the design; the engine and policy are the same ones scored on 91
  real days. Passengers are synthetic.
- **What if the agent rebooks someone who would have made it?** The original seat stays held until its gate
  closes; they keep their flight. On the real replay, 53 rebooked passengers made it and kept their flight.
