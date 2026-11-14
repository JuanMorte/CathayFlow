# Demo script (2 minutes)

Written for the presenter. **Fill every number from the running app and `data/evidence.json` once M9 passes**; never
from memory or from the trial. Placeholders look like `‹…›`.

**Setup (before going on stage)**
- Laptop: `/staff` on the AppUrl (or `OFFLINE=1 make demo` → http://localhost:8000/staff with Wi-Fi off).
- Phone: `/app` (opens as the scenario hero).
- In the staff console press **T−90**; keep the replay paused until you start talking.
- Never deploy during the demo.

**1. The passenger (0:00–0:20)** — "‹Hero› is flying ‹cabin› on ‹inbound flight› from ‹origin›, a real Cathay flight on
‹day›, connecting to ‹outbound› to ‹destination›, ‹gap› minutes later. ‹Hero› is synthetic; the flights and times are real."

**2. In the air (0:20–0:45)** — phone, *My trips*: the journey strip with the plane before HKG, the HKG time in orange.
"Your ‹destination› connection is tight": Plan A ‹likely %›, Plan B backup held on ‹flight time›, released automatically
if they board the original. Optional opener: *Home* ("Cathay Flow is on") or ⋯ → *Preview lock-screen alert*.

**3. Staff console (0:45–1:10)** — press **Before landing**. The inbound card shows the delay; the hero's row shows the
miss risk, impact and recommended backup. "The engine drafted these; a human approves." Click **Approve all**.

**4. Choose before you land (1:10–1:35)** — the phone shows the lock-screen alert *"Your options are ready"*. Tap it;
**Switch to ‹backup›** is now unlocked. Tap it, **Confirm switch**: *Board ‹backup› in …*; the staff row flips to
*Approved · Rebooked* within a second.

**5. Impact (1:35–2:00)** — `/impact`: ‹break rate, normal days› vs ‹disruption days›; on the scenario day Flow gave
‹n of m› missing passengers an approved plan before landing (today: ‹…›), with ‹…› wrong bumps versus ‹…› for an
auto-rebook.

**If asked**
- *Is this real?* Flights, times, stands, gates: HKIA public data; in-flight estimates: OAG. Passengers are synthetic;
  chances are simulated; transfer times are documented assumptions. Some passenger-app details are sample data (README).
- *Free seats?* OAG gives aircraft capacity, not availability; free seats are an assumption until Cathay's inventory is connected.
- *What if staff reject?* The backup stays held; nothing changes for the passenger until they choose.
