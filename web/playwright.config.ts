// One end-to-end test of the demo loop (AGENTS.md §15.7). Uses the installed Google Chrome, so no
// browser download. Run with `make e2e`; it starts its own offline backend on :8030.
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  workers: 1,
  timeout: 90_000,
  use: { baseURL: "http://localhost:8030", channel: "chrome" },
  webServer: {
    command: "cd .. && OFFLINE=1 FLOW_STATE_ENV=e2e uv run uvicorn app.main:app --app-dir backend --port 8030",
    url: "http://localhost:8030/api/health",
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
