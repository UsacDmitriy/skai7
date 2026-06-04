/**
 * cn — минимальный объединитель className (без зависимости от clsx).
 * Отбрасывает falsy-значения и склеивает оставшиеся строки через пробел.
 */
export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ')
}
