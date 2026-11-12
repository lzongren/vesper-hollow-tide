import { defineConfig } from "vite";
export default defineConfig({
  base: "./",
  resolve: { dedupe: ["three"] },
  optimizeDeps: {
    include: [
      "three",
      "three/addons/loaders/GLTFLoader.js",
      "three/addons/loaders/HDRLoader.js",
      "three/addons/utils/SkeletonUtils.js",
    ],
  },
  build: { target: "es2022", chunkSizeWarningLimit: 650 },
});
