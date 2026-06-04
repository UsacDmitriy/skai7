import type { Config } from 'tailwindcss'

/**
 * SKAI Online — дизайн-токены.
 * Источник истины: 00-CONTRACT.md §4 + init/context/DESIGN.md.
 *
 * Маппинг severity (API → токен) — единственно верный для всего фронта:
 *   critical → critical (красный)
 *   high     → high     (оранжевый)
 *   medium   → warning  (жёлтый)   ← ВАЖНО: medium НЕ имеет своего цвета
 *   low      → ok       (зелёный)  ← ВАЖНО: low → зелёный
 */
const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#1E3A8A',
          dark: '#1E3070',
          50: '#EFF6FF',
        },
        bg: '#F8FAFC',
        surface: '#FFFFFF',
        ink: '#0F172A',
        muted: '#64748B',
        border: '#E2E8F0',
        // Severity-палитра: DEFAULT = акцент (dot/border), bg = фон бейджа, text = текст бейджа
        critical: { DEFAULT: '#DC2626', bg: '#FEE2E2', text: '#991B1B' },
        high: { DEFAULT: '#EA580C', bg: '#FEF3C7', text: '#B45309' },
        warning: { DEFAULT: '#EAB308', bg: '#FEF9C3', text: '#854D0E' },
        ok: { DEFAULT: '#16A34A', bg: '#DCFCE7', text: '#166534' },
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
      },
      borderRadius: {
        md: '6px', // кнопки, карточки
        xl: '12px', // badge, modal
      },
    },
  },
  plugins: [],
}

export default config
