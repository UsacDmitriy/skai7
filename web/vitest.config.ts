import { fileURLToPath, URL } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Тесты двух типов под одним прогоном:
//  • чистые функции (роль-фильтр, парс персиста) — `src/**/*.test.ts`;
//  • компонентные (UI-примитивы, экраны) — `src/**/*.test.tsx` (jsdom + RTL).
// jsdom безопасен и для чистых функций, поэтому окружение единое. Алиас `@`
// совпадает с vite.config.ts. `VITE_USE_FIXTURES=true` — экраны работают без бэка.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    env: {
      VITE_USE_FIXTURES: 'true',
    },
  },
})
