import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  globalSetup: "./global-setup.ts",
  fullyParallel: false,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.API_BASE_URL ?? "http://localhost:8000",
    extraHTTPHeaders: { Accept: "application/json" },
  },
});
