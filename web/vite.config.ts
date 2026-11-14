/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: Vite on :5173, the backend on :8000 (`make dev`).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
  // Unit tests only; the browser test in e2e/ runs with `make e2e`.
  test: { environment: "jsdom", include: ["src/**/*.test.ts"] },
});
