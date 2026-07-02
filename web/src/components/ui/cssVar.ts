/**
 * Резолвит одиночный CSS-переменный цвет `var(--name)` в вычисленное значение.
 *
 * Нужен для Leaflet vector-слоёв: Leaflet кладёт fillColor/color в SVG-атрибут
 * `fill`/`stroke`, где `var()` НЕ резолвится (заливка становится чёрной). Здесь
 * подставляем реальное значение токена из :root.
 *
 * Фолбэк на исходную строку, если значение пустое (jsdom/SSR) или это не var(...).
 */
export function resolveCssColor(color: string): string {
  if (typeof document === 'undefined') return color

  const match = color.match(/^var\((--[\w-]+)\)$/)
  if (!match) return color

  const resolved = getComputedStyle(document.documentElement)
    .getPropertyValue(match[1])
    .trim()

  return resolved || color
}
