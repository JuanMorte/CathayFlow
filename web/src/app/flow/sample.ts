// Sample data for the passenger app (AGENTS.md §2.10 exception): details Cathay would hold but the
// demo does not, from the design (Figma "Cathay Hackathon 2026"). Flight times come from the API;
// everything here is either a fixed detail or an offset in minutes from those times.
export const SAMPLE = {
  miles: "48,210",
  statusPoints: "640",
  homeArea: "Kemang",
  homeCity: "Jakarta",
  leaveBeforeDepartureMin: 180,     // leave home this long before the first flight
  driveMin: 55,                     // home to the airport
  checkinCounter: "Business counter",
  checkinMin: 10,
  securityMin: 25,
  checkinToSecurityWalkMin: 12,
  originGate: "23",
  originWalkMin: 12,
  originBagsLoadedBeforeMin: 29,    // bags loaded this long before the first flight
  boardingBeforeMin: 35,
  atGateBeforeMin: 40,
  walkBufferMin: 15,                // reach the gate this long before boarding
  hkgWalkMinDefault: 18,
  onwardBagsLoadedBeforeMin: 34,
  hotline: "+852 9707 8071",
  bagTags: ["0125 849201", "0160 394812"],
  belt: "7",
  borderMin: 15,
  beltAfterLandingMin: 30,
  exitAfterBeltMin: 15,
  customsMin: 5,
  hotel: "Park Hyatt London",
  hotelDriveMin: 45,
  unloadedPercent: 50,
  beltEtaMin: 25,
  lastBagMaxMin: 45,
  originTerminalGateRange: "A14-19",
  airportNavMin: 2,
  prefs: { pace: "Relaxed", lounge: "The Pier, Business", diet: "Vegetarian", assistance: "None" },
};
