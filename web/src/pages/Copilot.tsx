import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  Bot,
  ExternalLink,
  RotateCcw,
  Send,
  Sparkles,
  User,
} from 'lucide-react'
import { detectLang, sendCopilotMessage } from '@/api/copilot'
import { ApiError } from '@/api/client'
import type { CopilotLang, CopilotMessage, CopilotToolCall } from '@/api/types'
import { Button, Card } from '@/components'
import { cn } from '@/components/ui/cn'

/**
 * f17 · Диалоговый AI-копилот по данным SKAI (`/copilot`, §8.3/§8.4, идея #13).
 * Поток: ввод (RU/EN) → `sendCopilotMessage` → ответ ассистента + связанные данные
 * (`tool_calls`/`data` рендерятся компактно со ссылкой на экран). Состояния §7.8:
 * idle/loading/ready/error(retry); пустой ввод заблокирован; язык ответа = языку запроса.
 * a11y: `role="dialog"` + лента `role="log"`/`aria-live`, фокус-менеджмент, Enter — отправить.
 * Эмиссия метрик b25 (`copilot_tool_*`) — внутри слоя `@/api/copilot`.
 */

// ── Двуязычные строки UI (хром панели; баблы рендерятся на языке сообщения) ─────
const UI = {
  ru: {
    title: 'AI-копилот',
    subtitle: 'Вопросы по данным парка на естественном языке',
    placeholder: 'Спросите про инциденты, риск, зоны…',
    send: 'Отправить',
    retry: 'Повторить',
    errorNetwork: 'Не удалось получить ответ. Проверьте соединение.',
    thinking: 'Копилот печатает…',
    emptyTitle: 'Чем помочь?',
    emptyHint: 'Спросите про риск, водителей или зоны — отвечу на языке вопроса.',
    related: 'Связанные данные',
    you: 'Вы',
    assistant: 'Копилот',
  },
  en: {
    title: 'AI Copilot',
    subtitle: 'Ask about fleet data in natural language',
    placeholder: 'Ask about incidents, risk, zones…',
    send: 'Send',
    retry: 'Retry',
    errorNetwork: 'Could not get a reply. Check your connection.',
    thinking: 'Copilot is typing…',
    emptyTitle: 'How can I help?',
    emptyHint: 'Ask about risk, drivers or zones — I reply in your language.',
    related: 'Related data',
    you: 'You',
    assistant: 'Copilot',
  },
} as const

// Подсказки для idle-состояния (двуязычные демо-запросы).
const SUGGESTIONS = [
  'Кто в группе риска?',
  'Покажи топ-3 водителей по риску',
  'Show high-risk zones tonight',
]

/** Связка инструмента копилота с экраном для drill-down (§8.4 tool_calls → ссылка). */
const TOOL_LINK: Record<string, { to: string; label: Record<CopilotLang, string> }> = {
  get_fleet_report: { to: '/report', label: { ru: 'Отчёт по парку', en: 'Fleet report' } },
  get_driver_report: { to: '/report', label: { ru: 'Отчёт по водителю', en: 'Driver report' } },
  get_forecast: { to: '/report', label: { ru: 'Прогноз риска', en: 'Risk forecast' } },
  get_zones: { to: '/monitor', label: { ru: 'Зоны на карте', en: 'Zones on map' } },
  list_incidents: { to: '/events', label: { ru: 'Лента инцидентов', en: 'Incident feed' } },
  get_incidents: { to: '/events', label: { ru: 'Лента инцидентов', en: 'Incident feed' } },
}

/** Достаёт первый строковый массив из `data` для компактной подписи (top/zones/…). */
function firstList(data: unknown): string[] | null {
  if (!data || typeof data !== 'object') return null
  for (const value of Object.values(data as Record<string, unknown>)) {
    if (Array.isArray(value) && value.every((v) => typeof v === 'string')) {
      return value as string[]
    }
  }
  return null
}

// ── Бабл одного сообщения ──────────────────────────────────────────────────────
function MessageBubble({ msg }: { msg: CopilotMessage }) {
  const isUser = msg.role === 'user'
  const t = UI[msg.lang]
  return (
    <div className={cn('flex gap-3', isUser ? 'flex-row-reverse' : 'flex-row')}>
      <div
        className={cn(
          'mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full',
          isUser ? 'bg-primary-50 text-primary' : 'bg-primary text-white',
        )}
        aria-hidden
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>
      <div className={cn('max-w-[78%] space-y-2', isUser && 'items-end')}>
        <div
          className={cn(
            'rounded-md px-3.5 py-2.5 text-sm leading-relaxed',
            isUser
              ? 'bg-primary text-white'
              : 'border border-border bg-surface text-ink',
          )}
        >
          <span className="sr-only">
            {isUser ? t.you : t.assistant}:{' '}
          </span>
          {msg.text}
        </div>
        {!isUser && <RelatedData msg={msg} />}
      </div>
    </div>
  )
}

// ── Компактный рендер `data`/`tool_calls` ответа + ссылки на экраны ─────────────
function RelatedData({ msg }: { msg: CopilotMessage }) {
  const calls = msg.tool_calls ?? []
  const list = firstList(msg.data)
  if (calls.length === 0 && !list) return null
  const t = UI[msg.lang]
  return (
    <Card className="!p-3">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-muted">
        <Sparkles size={13} aria-hidden />
        {t.related}
      </div>
      {list && (
        <p className="mt-1.5 text-sm text-ink">{list.join(' · ')}</p>
      )}
      {calls.length > 0 && (
        <ul className="mt-2 flex flex-wrap gap-2">
          {calls.map((call: CopilotToolCall, i) => {
            const link = TOOL_LINK[call.name]
            return (
              <li key={`${call.name}-${i}`}>
                {link ? (
                  <Link
                    to={link.to}
                    className="inline-flex items-center gap-1 rounded-md border border-border bg-bg px-2.5 py-1 text-xs font-medium text-primary transition-colors hover:border-primary"
                  >
                    {link.label[msg.lang]}
                    <ExternalLink size={12} aria-hidden />
                  </Link>
                ) : (
                  <span className="inline-flex items-center rounded-md border border-border bg-bg px-2.5 py-1 font-mono text-xs text-muted">
                    {call.name}
                  </span>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </Card>
  )
}

// ── Индикатор печати ассистента (loading) ──────────────────────────────────────
function TypingIndicator({ lang }: { lang: CopilotLang }) {
  return (
    <div className="flex gap-3" aria-label={UI[lang].thinking}>
      <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-primary text-white" aria-hidden>
        <Bot size={16} />
      </div>
      <div className="flex items-center gap-1 rounded-md border border-border bg-surface px-3.5 py-3" aria-hidden>
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  )
}

export default function Copilot() {
  const [messages, setMessages] = useState<CopilotMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Язык последней реплики пользователя — для строк хрома и ретрая.
  const [uiLang, setUiLang] = useState<CopilotLang>('ru')
  const lastQuery = useRef<string | null>(null)

  const inputRef = useRef<HTMLTextAreaElement>(null)
  const endRef = useRef<HTMLDivElement>(null)
  const t = UI[uiLang]

  // Автофокус на поле ввода при открытии панели.
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // Прокрутка ленты к последнему сообщению / индикатору печати.
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  const ask = useCallback(async (text: string) => {
    const lang = detectLang(text)
    lastQuery.current = text
    setUiLang(lang)
    setError(null)
    setMessages((prev) => [...prev, { role: 'user', text, lang }])
    setLoading(true)
    try {
      const reply = await sendCopilotMessage(text)
      setMessages((prev) => [...prev, reply])
    } catch (e: unknown) {
      const msg =
        e instanceof ApiError
          ? e.message
          : UI[lang].errorNetwork
      setError(msg)
    } finally {
      setLoading(false)
      // Возврат фокуса в поле ввода после ответа (фокус-менеджмент a11y).
      inputRef.current?.focus()
    }
  }, [])

  const submit = useCallback(() => {
    const text = input.trim()
    if (!text || loading) return // пустой ввод заблокирован
    setInput('')
    void ask(text)
  }, [input, loading, ask])

  const retry = useCallback(() => {
    if (lastQuery.current) void ask(lastQuery.current)
  }, [ask])

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const isEmpty = messages.length === 0 && !loading && !error

  return (
    <section
      role="dialog"
      aria-label={t.title}
      className="mx-auto flex h-full max-w-3xl flex-col"
    >
      {/* Заголовок панели */}
      <header className="flex items-center gap-3 border-b border-border pb-3">
        <div className="grid h-10 w-10 place-items-center rounded-xl bg-primary-50 text-primary" aria-hidden>
          <Bot size={20} strokeWidth={1.75} />
        </div>
        <div>
          <h1 className="text-[18px] font-semibold text-ink">{t.title}</h1>
          <p className="text-[13px] text-muted">{t.subtitle}</p>
        </div>
      </header>

      {/* Лента сообщений — role=log + aria-live для скринридера */}
      <div
        role="log"
        aria-live="polite"
        aria-relevant="additions"
        aria-busy={loading}
        className="flex-1 space-y-4 overflow-y-auto py-4"
      >
        {isEmpty ? (
          <div className="grid h-full place-items-center">
            <div className="max-w-md px-4 text-center">
              <div className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-primary-50 text-primary">
                <Sparkles className="h-6 w-6" strokeWidth={1.75} aria-hidden />
              </div>
              <div className="mt-4 text-[16px] font-semibold text-ink">{t.emptyTitle}</div>
              <p className="mt-1 text-[13px] leading-relaxed text-muted">{t.emptyHint}</p>
              <ul className="mt-4 flex flex-wrap justify-center gap-2">
                {SUGGESTIONS.map((s) => (
                  <li key={s}>
                    <button
                      type="button"
                      onClick={() => void ask(s)}
                      className="rounded-full border border-border bg-surface px-3 py-1.5 text-[13px] text-ink transition-colors hover:border-primary hover:text-primary"
                    >
                      {s}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <MessageBubble key={i} msg={msg} />
            ))}
            {loading && <TypingIndicator lang={uiLang} />}
          </>
        )}
        <div ref={endRef} />
      </div>

      {/* Плашка ошибки + повтор */}
      {error && (
        <div
          role="alert"
          className="mb-3 flex items-center justify-between gap-3 rounded-md border border-critical-bg bg-critical-bg px-3.5 py-2.5"
        >
          <span className="flex items-center gap-2 text-sm text-critical-text">
            <AlertTriangle size={16} aria-hidden />
            {error}
          </span>
          <Button variant="secondary" icon={RotateCcw} onClick={retry}>
            {t.retry}
          </Button>
        </div>
      )}

      {/* Ввод: Enter — отправить, Shift+Enter — перенос строки */}
      <form
        onSubmit={(e) => {
          e.preventDefault()
          submit()
        }}
        className="flex items-end gap-2 border-t border-border pt-3"
      >
        <label htmlFor="copilot-input" className="sr-only">
          {t.placeholder}
        </label>
        <textarea
          id="copilot-input"
          ref={inputRef}
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={t.placeholder}
          className="max-h-32 min-h-9 flex-1 resize-none rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink outline-none transition-colors placeholder:text-muted focus:border-primary"
        />
        <Button
          type="submit"
          icon={Send}
          loading={loading}
          disabled={input.trim().length === 0}
          aria-label={t.send}
        />
      </form>
    </section>
  )
}
