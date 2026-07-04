import { fileURLToPath, URL } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  // Pre-bundle тяжёлые deps для быстрого холодного старта и HMR.
  // Recharts, Leaflet, lucide-react — самые крупные в проекте.
  optimizeDeps: {
    include: ['recharts', 'leaflet', 'lucide-react', 'react-leaflet'],
  },
  server: {
    port: 5173,
    // Прокси к FastAPI: фронт ходит на /api без CORS-проблем.
    // Target берётся из VITE_API_TARGET, дефолт — http://localhost:8000.
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
