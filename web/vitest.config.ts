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
    // Гейт покрытия фронта (w3-4, проверяется на Барьере 3/x5): `npx vitest run --coverage`.
    // Поверхность w3-4 — примитивы d3–d5 и экраны f5–f13. Из измерения исключены:
    //  • bootstrap/типы/витрина/re-export-бочки и App-каркас (зона f1 — статический layout);
    //  • экраны других промптов волны 3/4 — их покрывают СВОИ тест-промпты:
    //    w3-11 «Здоровье парка» (FleetHealth/FuelCard/SensorCard/NavProblemList/ComingSoon) → w3-15;
    //    заглушки Copilot/Metrics (волна 4) → свои промпты. Дублировать их здесь не наша зона.
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/main.tsx',
        'src/vite-env.d.ts',
        'src/App.tsx',
        'src/pages/_StyleGuide.tsx',
        'src/components/index.ts',
        'src/components/map/index.ts',
        'src/api/types.ts',
        'src/components/map/types.ts',
        // Экраны вне scope w3-4 (свои тест-промпты в волне 3/4):
        'src/pages/FleetHealth.tsx',
        'src/pages/FuelCard.tsx',
        'src/pages/SensorCard.tsx',
        'src/pages/NavProblemList.tsx',
        'src/pages/Copilot.tsx',
        'src/pages/Metrics.tsx',
        'src/components/ComingSoon.tsx',
        'src/**/*.test.{ts,tsx}',
        'src/test/**',
      ],
      // Гейт Check w3-4 — единый порог «≥80%» (= строки/операторы); ветки тоже ≥80%.
      // `functions` не гейтим: метрика занижена инлайн render-хелперами экранов и
      // сетевыми функциями f2-`client.ts` (живой режим покрыт client.test.ts/t3, не зона w3-4).
      thresholds: { lines: 80, statements: 80, branches: 80 },
    },
  },
})
