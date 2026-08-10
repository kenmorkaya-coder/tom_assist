import { defineConfig } from "vite";
import preact from "@preact/preset-vite";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const currentDirectory = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  plugins: [preact()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        sidepanel: resolve(currentDirectory, "sidepanel.html"),
        background: resolve(currentDirectory, "src/background.ts"),
        content: resolve(currentDirectory, "src/content.tsx"),
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "chunks/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
});
