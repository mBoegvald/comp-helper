import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vitest/config";

// The build goes to ../web/dist, which is committed: the Windows PC runs it without Node.
// `npm run dev` serves the page with hot reload and forwards /api to `python webapp.py --no-browser`.
export default defineConfig({
  plugins: [svelte()],
  base: "./",
  build: { outDir: "../web/dist", emptyOutDir: true },
  server: { proxy: { "/api": "http://127.0.0.1:8765" } },
  test: { include: ["src/**/*.test.ts"], environment: "node" },
});
