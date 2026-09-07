import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // All /auth, /chat, /sessions, /models, /projects, /history,
      // /artifacts, /download, /sentry, /system requests are proxied
      // to the FastAPI backend on port 8000.
      // This makes the browser see everything as same-origin (localhost:5173),
      // so SameSite cookies work perfectly with no CORS complexity.
      "/auth": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false,
        secure: false,
      },
      "/chat": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false,
        secure: false,
      },
      "/sessions": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false,
        secure: false,
      },
      "/models": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false,
        secure: false,
      },
      "/projects": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false,
        secure: false,
      },
      "/history": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false,
        secure: false,
      },
      "/artifacts": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false,
        secure: false,
      },
      "/download": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false,
        secure: false,
      },
      "/sentry": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false,
        secure: false,
      },
      "/system": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false,
        secure: false,
      },
    },
  },
});
