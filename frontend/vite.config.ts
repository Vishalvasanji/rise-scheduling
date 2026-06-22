import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite SPA consuming the FastAPI JSON API. The API base URL is read from
// VITE_API_BASE_URL (env), defaulting to the local backend.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
