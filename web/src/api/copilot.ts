/**
 * f17 · Тонкий слой копилота над f2-клиентом (`POST /api/copilot/chat`, §8.3/§8.4).
 *
 * Сетевой вызов и подмена на фикстуры (`VITE_USE_FIXTURES`, детерминированные ответы по
 * языку запроса) живут в f2 `client.copilotChat` — здесь только оркестрация и телеметрия b25:
 * на каждый вызванный инструмент эмитим `copilot_tool_called`, при наличии полезного груза —
 * `copilot_tool_success` (§8.7, питает одноимённый KPI). Эмиттер `@/api/metrics` fire-and-forget,
 * без сети — no-op.
 */
import { copilotChat } from './client'
import { trackEvent } from './metrics'
import type { CopilotLang, CopilotMessage } from './types'

/** Кириллица в реплике → язык запроса (та же эвристика, что у фикстур/бэкенда §8.4). */
const CYRILLIC = /[А-Яа-яЁё]/

/** Язык реплики пользователя — для бабла запроса и выбора строк UI до прихода ответа. */
export function detectLang(text: string): CopilotLang {
  return CYRILLIC.test(text) ? 'ru' : 'en'
}

/**
 * Реплика пользователя → ответ ассистента (§8.4). Язык ответа задаёт бэкенд/фикстуры
 * по языку запроса (поле `lang`). На каждый `tool_call` эмитит `copilot_tool_called`;
 * если ответ принёс полезный груз (`data`) — `copilot_tool_success` (§8.7).
 */
export async function sendCopilotMessage(text: string): Promise<CopilotMessage> {
  const reply = await copilotChat(text)
  const succeeded = reply.data != null
  for (const call of reply.tool_calls ?? []) {
    trackEvent('copilot_tool_called', { tool: call.name })
    if (succeeded) trackEvent('copilot_tool_success', { tool: call.name })
  }
  return reply
}
