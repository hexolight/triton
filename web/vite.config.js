import { defineConfig } from "vite";

export default defineConfig({
  // @ffmpeg/ffmpeg spawns its own module worker from a path relative to itself;
  // pre-bundling it breaks that path, so leave both packages as they are.
  optimizeDeps: { exclude: ["@ffmpeg/ffmpeg", "@ffmpeg/util"] },
  worker: { format: "es" },
  build: { target: "es2022", chunkSizeWarningLimit: 1500 },
  test: { environment: "node" },
});
