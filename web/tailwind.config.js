/** Tokens from docs/design/README.md. Light only (AGENTS.md §17.6.1). */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      // The design uses Sofia Pro (commercial); Jost is the closest free match and is already in the design.
      fontFamily: { sans: ["system-ui", "-apple-system", "sans-serif"], jost: ["Jost", "system-ui", "sans-serif"],
        figtree: ["Figtree", "system-ui", "sans-serif"] },
      colors: {
        page: "#F9F8F6",
        staffpage: "#F4F3F0",
        ink: "#262425",
        muted: "#595959",
        nav: "#616163",
        deep: "#2F625D",
        primary: "#367877",
        late: "#AE4B07",
        amber: "#C9822B",
        ok: { DEFAULT: "#2E7D4F", bg: "#E6F2EA" },
        mint: "#D7E5E5",
        line: "#E4E2DE",
        info: "#E9F3F5",
        warn: { DEFAULT: "#F5F1E3", text: "#7F652D" },
        planA: { bg: "#E3EEEE", text: "#2F625D" },
        planB: { bg: "#F5EDDA", text: "#88661F" },
        button: "#2C4035",
        jade: "#006564",
        saffron: "#C2262E",
        heroFrom: "#2E7173",
        heroTo: "#0C6166",
      },
    },
  },
  plugins: [],
};
