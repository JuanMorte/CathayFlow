# Design: Cathay Flow (Figma "Cathay Hackathon 2026")

The screens in this folder are PNG exports of the team's Figma file (`N1qBXbnt8bpFOSsbOmXrcN`). They are the
reference every UI change is checked against (AGENTS.md §3). Phone frames are 393 × 852; the staff frame is
1280 × 820. The implementation lives in `web/src/app/flow/` (passenger) and `web/src/staff/` (staff).

## Screens

| File | Figma node | Screen | Code |
|---|---|---|---|
| `s1-home.png` | 4165-242 | Cathay app home, upcoming journey card with the "Cathay Flow is on" entry | `flow/home.tsx` `HomeScreen` |
| `s2-setup.png` | | Set up Cathay Flow (travelling with, pace, lounge, bags, alerts, privacy) | `flow/home.tsx` `SetupScreen` |
| `s3-prepare.png` | | Prepare: leave home at, step-by-step origin-airport timeline | `flow/prepare.tsx` |
| `s4-lockscreen.png` | | Lock-screen notification: tight connection, bags loaded | `flow/home.tsx` `LockAlert` |
| `s5-protect-in-flight.png` | 4168-435 | Connect (in flight): Plan A / Plan B, keep both or switch | `flow/connect.tsx` |
| `s6-navigate.png` | 4168-558, 4180-256 | Navigate in the HKG transfer: walk, gate closes, spare, route and pier map | `flow/navigate.tsx` |
| `s7-bags.png` | | Bags: tags, status pills, scan timeline | `flow/bags.tsx` |
| `s7b-plan-b.png` | 4168-703 | Plan B confirmed: board in, new flight, seat, bags, lounge, boarding pass | `flow/planb.tsx` |
| `s8-arrival.png` | | Arrival Mode: exit by, border, belt, getting to the hotel | `flow/arrive.tsx` |
| `staff-flow-ops.png` | | Flow Ops staff console: inbound-delay card, risk table, approve all | `web/src/staff/StaffConsole.tsx` |
| `brand-palette.png` | | Cathay brand colours (Pantone / CMYK / RGB) | `web/tailwind.config.js` |
| `icons.png` | | Icon sheet | `flow/kit.tsx` |

## Building blocks

- **Font:** Figtree (400/500/600/700, `@fontsource/figtree` 5.3.0). Titles 17 px bold, body 13.5–15.5 px, hero numbers 44–52 px bold.
- **Journey strip:** Home → origin airport → HKG → destination → Exit, a time under each stop, the plane on the line
  while flying, late times bold in `#AE4B07`. Tapping a stop opens its screen.
- **Header:** mint `#D7E5E5` with a soft circle top-right, back arrow, centred title + subtitle, "⋯" menu.
- **Hero card:** gradient `#2E7173 → #0C6166`, white pill tag (CONNECT, NAVIGATE, PLAN B, BAGS, ARRIVE, PREPARE), white text.
- **Cards:** white, 12 px radius, 1 px border `#E4E2DE`. Notices: info `#E9F3F5`, warning `#F5F1E3` / text `#7F652D`.
- **Buttons:** primary dark green `#2C4035`, 8 px radius, 50 px tall; secondary outlined `#367877`.
- **Bottom navigation (Cathay app):** Home, Book, My trips, Profile, Travel tools; active `#367877` bold.

## Colour tokens

| Token | Hex | Use |
|---|---|---|
| page | `#F9F8F6` | passenger background (staff `#F4F3F0`) |
| ink / muted / nav | `#262425` / `#595959` / `#616163` | text |
| deep / primary | `#2F625D` / `#367877` | headings, strip, links, outlines |
| late | `#AE4B07` | late times, high impact, priority |
| amber | `#C9822B` | medium risk |
| ok | `#2E7D4F` (bg `#E6F2EA`) | likely, approved, loaded |
| Plan A pill | `#E3EEEE` / `#2F625D` | |
| Plan B pill | `#F5EDDA` / `#88661F` | |
| Cathay Jade | `#006564` | brand (boarding pass, logo disc) |
| Cathay Saffron | `#C2262E` | errors, notification dot |

## Data rules for the design

The mockups show illustrative values (Jakarta → London, CX718, 62% likely). The app shows **API data** in the same
slots. Details the design needs but no source has (miles, terminals, lounge, walking pace, bags, origin departure and
destination arrival times, arrival queues, taxi times) are sample data from `web/src/app/flow/sample.ts`, disclosed in
`README.md` (AGENTS.md non-negotiables 6 and 10, amended 2026-11-13).
