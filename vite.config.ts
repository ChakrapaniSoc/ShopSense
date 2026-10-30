import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import path from "node:path"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  server: { host: "0.0.0.0", port: 5174, strictPort: true, proxy: { "/api": "http://127.0.0.1:8001" } },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          const file = id.replaceAll("\\", "/")
          if (/\/node_modules\/(recharts|victory-vendor|d3-[^/]+)\//.test(file)) return "charts"
          if (/\/node_modules\/(react|react-dom|scheduler)\//.test(file)) return "react-vendor"
        },
      },
    },
  },
})
