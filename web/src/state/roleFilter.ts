/**
 * f13 · Чистые правила фильтрации/представления по роли (идея #10).
 *
 * Одна лента/карта — три роли видят разное. Все функции **чистые и
 * детерминированные** (без `Date.now()`, без мутаций входа) — покрыты юнит-тестами
 * и применяются согласованно в ленте (`filterByRole`) и на карте
 * (`markerOptionsForRole`, `dedupeByUnit`).
 */
import type { Severity, Source } from '@/api/types'
import type { Role } from '@/components/map/types'

// ── Лента инцидентов ──────────────────────────────────────────────────────────

/** Минимальная форма инцидента для ролевой фильтрации (IncidentSummary её удовлетворяет). */
export interface RoleFilterable {
  source: Source
  risk_score: number
}

/** Видео-источники, приоритетные для Безопасника. */
const VIDEO_SOURCES: ReadonlySet<Source> = new Set<Source>(['DMS', 'ADAS'])

/** Числовой risk_score с фолбэком 0 (защита от undefined/NaN → стабильная сортировка). */
function safeRisk(score: number): number {
  return Number.isFinite(score) ? score : 0
}

/**
 * Правила ленты по роли:
 *  • Логист — скрывает `source=DMS` (нет доступа к DMS-алармам).
 *  • Диспетчер — полный список без изменений порядка.
 *  • Безопасник — акцент на риск: видеоалармы (DMS/ADAS) в приоритете отображения,
 *    затем по `risk_score` desc. Стабильно при отсутствующем `risk_score`.
 *
 * Не мутирует вход; возвращает новый массив.
 */
export function filterByRole<T extends RoleFilterable>(
  role: Role,
  items: readonly T[],
): T[] {
  switch (role) {
    case 'logist':
      return items.filter((i) => i.source !== 'DMS')
    case 'security': {
      // index-tiebreak → детерминированный стабильный порядок при равных ключах.
      return items
        .map((item, index) => ({ item, index }))
        .sort((a, b) => {
          const va = VIDEO_SOURCES.has(a.item.source) ? 1 : 0
          const vb = VIDEO_SOURCES.has(b.item.source) ? 1 : 0
          if (va !== vb) return vb - va
          const ra = safeRisk(a.item.risk_score)
          const rb = safeRisk(b.item.risk_score)
          if (ra !== rb) return rb - ra
          return a.index - b.index
        })
        .map(({ item }) => item)
    }
    case 'dispatcher':
    default:
      return [...items]
  }
}

// ── Карта: опции отображения маркеров по роли ─────────────────────────────────

/** Как красить маркеры: по статусу online/offline или по severity. */
export interface MarkerOptions {
  colorBy: 'severity' | 'status'
  /** Поднять видеоалармы (DMS/ADAS) на первый план (Безопасник). */
  emphasizeVideo: boolean
}

/**
 * Опции слоя маркеров по роли:
 *  • Логист — только online/offline (без severity-цвета).
 *  • Диспетчер — цвет по severity.
 *  • Безопасник — severity + акцент на видео.
 */
export function markerOptionsForRole(role: Role): MarkerOptions {
  switch (role) {
    case 'logist':
      return { colorBy: 'status', emphasizeVideo: false }
    case 'security':
      return { colorBy: 'severity', emphasizeVideo: true }
    case 'dispatcher':
    default:
      return { colorBy: 'severity', emphasizeVideo: false }
  }
}

// ── Дедупликация ТС: 1 unit_id = 1 объект ─────────────────────────────────────

/** Минимальная форма для дедупа (MapUnit/IncidentDetail её удовлетворяют). */
export interface UnitDedupable {
  unit_id?: string | null
  severity?: Severity
  ts?: string
}

/** Ранг severity для выбора наихудшего алярма; неизвестный/отсутствующий → 0. */
const SEVERITY_RANK: Record<Severity, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
}

function severityRank(severity: Severity | undefined): number {
  return severity ? (SEVERITY_RANK[severity] ?? 0) : 0
}

/**
 * Дедуп по `unit_id`: ровно один объект на ТС (на карте — 1 маркер, НЕ на каждый
 * `AlarmId`). Остаётся наихудший по severity; при равной severity — более поздний
 * `ts`; при равенстве — последний встреченный.
 *
 * Устойчив к грязным данным: записи с null/undefined/пустым `unit_id` отбрасываются
 * (без них маркер не разместить), отсутствующая severity/ts не вызывают NaN и не
 * плодят дубли. Не мутирует вход.
 */
export function dedupeByUnit<T extends UnitDedupable>(items: readonly T[]): T[] {
  const byUnit = new Map<string, T>()
  for (const item of items) {
    const id = item.unit_id
    if (id == null || id === '') continue
    const prev = byUnit.get(id)
    if (!prev) {
      byUnit.set(id, item)
      continue
    }
    const rank = severityRank(item.severity)
    const prevRank = severityRank(prev.severity)
    if (rank > prevRank) {
      byUnit.set(id, item)
    } else if (rank === prevRank && (item.ts ?? '') >= (prev.ts ?? '')) {
      // равная severity → более поздний ts; при равенстве — последний встреченный.
      byUnit.set(id, item)
    }
  }
  return [...byUnit.values()]
}
