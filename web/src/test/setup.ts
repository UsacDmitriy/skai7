/**
 * t3 · Глобальный setup для компонентных тестов (vitest + RTL, jsdom).
 *  • подключает jest-dom matchers (`toBeInTheDocument`, `toHaveClass`…);
 *  • чистит DOM после каждого теста (изоляция);
 *  • полифилит то, чего нет в jsdom, но требуют продуктовые компоненты:
 *    ResizeObserver (recharts), scrollIntoView (таблицы/лента), matchMedia.
 */
import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => {
  cleanup()
})

// recharts ResponsiveContainer наблюдает размер контейнера — в jsdom ResizeObserver нет.
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
globalThis.ResizeObserver =
  globalThis.ResizeObserver ?? (ResizeObserverStub as unknown as typeof ResizeObserver)

// jsdom не реализует scrollIntoView — Monitor/Report зовут его при выборе строки/маркера.
Element.prototype.scrollIntoView = vi.fn()

// Часть компонентов может читать matchMedia — отдаём безопасную заглушку.
if (typeof window.matchMedia !== 'function') {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia
}
