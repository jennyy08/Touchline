import { defineConfig } from "vite";
export default defineConfig({
  server: { proxy: { "/api": { target: "http://127.0.0.1:8000", ws: true } } },
  build: {
    rollupOptions: {
      input: {
        main: "index.html",
        juggling: "juggling.html",
        drill: "drill.html",
        session: "session.html",
        live: "live.html",
        dribbling: "dribbling.html",
        toeTaps: "toe-taps.html",
      },
    },
  },
});
