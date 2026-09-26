import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// MedTrace frontend. The backend base URL is read at runtime from
// VITE_API_BASE_URL (see .env.example) and defaults to
// http://127.0.0.1:8000 inside src/services/api.ts — nothing here needs
// to change to point at a different backend host.
export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
    },
});
