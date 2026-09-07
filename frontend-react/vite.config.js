import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  // Backend target for the dev proxy.
  // Override with VITE_BACKEND_URL in a .env file if you need to point
  // at a remote backend (e.g. when sharing across a LAN).
  const backendTarget = env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

  // All API path prefixes that should be forwarded to the backend.
  const apiPaths = [
    "/auth",
    "/chat",
    "/sessions",
    "/models",
    "/projects",
    "/history",
    "/artifacts",
    "/download",
    "/sentry",
    "/system",
    "/users",
  ];

  const proxyRules = Object.fromEntries(
    apiPaths.map((path) => [
      path,
      {
        target: backendTarget,
        // changeOrigin: true rewrites the Host header to match the backend,
        // which is required when backendTarget is a remote machine.
        changeOrigin: true,
        secure: false,
      },
    ])
  );

  return {
    plugins: [react()],
    server: {
      // Bind to all interfaces so teammates on the same LAN can reach the
      // Vite dev server at http://YOUR_LAN_IP:5173.
      host: "0.0.0.0",
      port: 5173,
      proxy: proxyRules,
    },
  };
});
