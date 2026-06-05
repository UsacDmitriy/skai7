import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'

// Юнит-тесты чистых функций (роль-фильтр, парсинг персиста) — node-окружение,
// без jsdom. Алиас `@` совпадает с vite.config.ts.
export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
