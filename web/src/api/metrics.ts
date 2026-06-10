/**
 * b25 · тонкий клиентский эмиттер AI-метрик → `POST /api/metrics/event`.
 *
 * Продьюсеры (f16 рекомендации, f17 копилот, f18 зоны) вызывают `trackEvent(name, payload)`
 * при ключевых действиях; бэкенд пишет в `ai_metric_events`, из которых считается `AiMetrics`
 * (§8.7). Fire-and-forget: ошибки сети глотаются, UI никогда не блокируется.
 *
 * Без сети (`VITE_USE_FIXTURES=true`) — no-op: метрики не имеют смысла на статичных фикстурах.
 */

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api'
const USE_FIXTURES = import.meta.env.VITE_USE_FIXTURES === 'true'

/** Имена событий AI-слоя (§8.7 / b25). */
export type AiMetricEvent =
  | 'recommendation_shown'
  | 'recommendation_accepted'
  | 'copilot_tool_called'
  | 'copilot_tool_success'
  | 'zone_opened'
  | 'weather_mismatch'

/**
 * Зафиксировать AI-событие. No-op в режиме фикстур; иначе — fire-and-forget POST.
 * Никогда не бросает и не возвращает промис, чтобы не влиять на поток UI.
 */
export function trackEvent(name: AiMetricEvent, payload?: Record<string, unknown>): void {
  if (USE_FIXTURES) return
  try {
    void fetch(`${BASE}/metrics/event`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, payload }),
      keepalive: true,
    }).catch(() => {
      /* метрики необязательны — сеть может быть недоступна */
    })
  } catch {
    /* fetch недоступен (SSR/тест) — тихо игнорируем */
  }
}
