import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// build estático simples, embutido no executável e servido pelo próprio
// FastAPI local (seção 1/6) — sem SSR, sem servidor Node em produção.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // só em dev (`npm run dev`); em produção o build estático é
      // servido pelo próprio FastAPI, então /api/v1 já é same-origin.
      "/api/v1": "http://127.0.0.1:8000",
    },
  },
});
