import { useAsyncLoad } from '@/state/useAsyncLoad'
import { Inbox, RotateCcw, TriangleAlert } from 'lucide-react'
import { Button, Card } from '@/components'
import { DataQualityPanel, MetricTile, formatRatio } from '@/components/ai/DataQualityPanel'
import { ConsistencyPanel } from '@/components/ai/ConsistencyPanel'
import { getAiMetrics, getConsistency, getDataQuality } from '@/api/client'
import type { AiMetrics, DataQuality } from '@/api/types'

/**
 * f21 · Панель доверия и пользы (`/metrics`). Против `00-CONTRACT.md` §8.7.
 *
 * KPI AI-слоя (`GET /api/metrics/ai`) + качество данных
 * (`GET /api/metrics/data-quality`) для безопасника/диспетчера/PO. Работает на
 * живом API и на фикстурах (`VITE_USE_FIXTURES`). Маршрут и пункт меню заведены
 * заранее (w3-18) — здесь только содержимое, без правок роутинга.
 */

// ── KPI AI-слоя (§8.7): нейтральные плитки, без светофора ──────────────────────

interface AiKpi {
  key: keyof AiMetrics
  label: string
  kind: 'ratio' | 'duration'
  sub: string
}

const AI_KPIS: AiKpi[] = [
  {
    key: 'recommendation_acceptance',
    label: 'Принятие рекомендаций',
    kind: 'ratio',
    sub: 'Доля принятых подсказок ассистента',
  },
  {
    key: 'copilot_tool_success',
    label: 'Успех инструментов копилота',
    kind: 'ratio',
    sub: 'Доля удачных вызовов tool-call',
  },
  {
    key: 'zone_hit_rate',
    label: 'Попадание в зоны',
    kind: 'ratio',
    sub: 'Инциденты внутри размеченных зон',
  },
  {
    key: 'forecast_coverage',
    label: 'Покрытие прогнозом',
    kind: 'ratio',
    sub: 'Доля ТС с активным прогнозом',
  },
  {
    key: 'weather_mismatch_rate',
    label: 'Рассогласование погоды',
    kind: 'ratio',
    sub: 'Сцена ↔ метеоданные расходятся',
  },
  {
    key: 'avg_time_to_triage',
    label: 'Время до триажа',
    kind: 'duration',
    sub: 'Среднее от алярма до решения',
  },
]

/** Секунды → «N мин M сек» / «N сек». Детерминированно, без локали времени. */
function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)} сек`
  const min = Math.floor(seconds / 60)
  const sec = Math.round(seconds % 60)
  return sec === 0 ? `${min} мин` : `${min} мин ${sec} сек`
}

function kpiValue(kpi: AiKpi, m: AiMetrics): string {
  return kpi.kind === 'duration' ? formatDuration(m[kpi.key]) : formatRatio(m[kpi.key])
}

/** Метрики «пусты», если событий ещё не было (все нули) → empty-state. */
function isAiMetricsEmpty(m: AiMetrics): boolean {
  return AI_KPIS.every((k) => m[k.key] === 0)
}

// ── Состояние загрузки ─────────────────────────────────────────────────────────

function TilesSkeleton({ count }: { count: number }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-hidden>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="h-[104px] animate-pulse rounded-xl border border-border bg-border/40" />
      ))}
    </div>
  )
}

// ── Экран ────────────────────────────────────────────────────────────────────

interface MetricsData {
  ai: AiMetrics
  quality: DataQuality
}

export default function Metrics() {
  const { state, data, error, reload } = useAsyncLoad<MetricsData>(
    () =>
      Promise.all([getAiMetrics(), getDataQuality()]).then(([ai, quality]) => ({ ai, quality })),
    { errorMessage: 'Не удалось загрузить метрики.' },
  )
  // f25 · консистентность (§10) грузится независимо и мягко: её ошибка → data=null
  // (панель-заглушка), страницу метрик не ломает.
  const { data: consistency } = useAsyncLoad(getConsistency)

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-lg font-bold text-ink">Метрики и качество данных</h1>
        <p className="text-sm text-muted">
          Доверие и польза AI-слоя: KPI моделей и качество дата-слоя (камеры, GPS, медиа, погода).
          Доли показаны в процентах; низкое качество данных подсвечено.
        </p>
      </header>

      {state === 'error' ? (
        <Card className="flex flex-col items-center gap-3 py-12 text-center">
          <TriangleAlert className="h-8 w-8 text-high-text" aria-hidden />
          <p className="max-w-sm text-sm text-muted">{error ?? 'Не удалось загрузить метрики.'}</p>
          <Button variant="secondary" icon={RotateCcw} onClick={reload}>
            Повторить
          </Button>
        </Card>
      ) : (
        <>
          {/* KPI AI-слоя */}
          <section className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">KPI AI-слоя</h2>
            {state === 'loading' ? (
              <TilesSkeleton count={6} />
            ) : data && isAiMetricsEmpty(data.ai) ? (
              <Card className="flex flex-col items-center gap-2 py-12 text-center text-muted">
                <Inbox className="h-8 w-8" aria-hidden />
                <p className="text-sm">Пока нет событий AI-слоя — метрики появятся после первых действий.</p>
              </Card>
            ) : data ? (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {AI_KPIS.map((kpi) => (
                  <MetricTile
                    key={kpi.key}
                    label={kpi.label}
                    value={kpiValue(kpi, data.ai)}
                    sub={kpi.sub}
                  />
                ))}
              </div>
            ) : null}
          </section>

          {/* Качество данных */}
          <section className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
              Качество данных
            </h2>
            {state === 'loading' ? (
              <TilesSkeleton count={5} />
            ) : data ? (
              <DataQualityPanel data={data.quality} />
            ) : null}
          </section>

          {/* Консистентность данных (§10, f25): светофор по 7 проверкам + сводные доли */}
          <section className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
              Консистентность данных
            </h2>
            {state === 'loading' ? (
              <TilesSkeleton count={2} />
            ) : (
              <ConsistencyPanel data={consistency} />
            )}
          </section>
        </>
      )}
    </div>
  )
}
