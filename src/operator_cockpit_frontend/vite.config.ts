import { defineConfig } from "vite";

// Local development only. The application always calls same-origin /api; the dev server binds
// loopback and forwards /api to the loopback cockpit backend. No other proxy, host or credential.
export default defineConfig({
  // public/ only carries the Storybook MSW worker; it must not ship in the production build.
  publicDir: false,
  server: {
    host: "127.0.0.1",
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false,
      },
    },
  },
  preview: {
    host: "127.0.0.1",
    strictPort: true,
  },
});
