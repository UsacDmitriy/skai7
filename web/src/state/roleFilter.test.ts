import { describe, expect, it } from 'vitest'
import type { Source } from '@/api/types'
import { dedupeByUnit, filterByRole, markerOptionsForRole } from './roleFilter'

// ── filterByRole (лента) ──────────────────────────────────────────────────────
describe('filterByRole', () => {
  interface Row {
    id: string
    source: Source
    risk_score: number
  }
  const mk = (id: string, source: Source, risk_score: number): Row => ({
    id,
    source,
    risk_score,
  })

  const items = [
    mk('a', 'DMS', 80),
    mk('b', 'TELEMATICS', 20),
    mk('c', 'ADAS', 50),
    mk('d', 'DMS', 90),
  ]

  it('Логист: скрывает source=DMS', () => {
    const res = filterByRole('logist', items)
    expect(res.map((i) => i.id)).toEqual(['b', 'c'])
    expect(res.every((i) => i.source !== 'DMS')).toBe(true)
  })

  it('Диспетчер: без фильтра и без переупорядочивания', () => {
    const res = filterByRole('dispatcher', items)
    expect(res.map((i) => i.id)).toEqual(['a', 'b', 'c', 'd'])
  })

  it('Безопасник: видеоалармы (DMS/ADAS) в приоритете, затем по risk_score desc', () => {
    const res = filterByRole('security', items)
    // видео-источники первыми (d:90, a:80, c:50), затем телематика (b:20)
    expect(res.map((i) => i.id)).toEqual(['d', 'a', 'c', 'b'])
  })

  it('Безопасник: детерминированная сортировка при отсутствующем risk_score', () => {
    const partial = [
      mk('x', 'TELEMATICS', undefined as unknown as number),
      mk('y', 'TELEMATICS', undefined as unknown as number),
    ]
    const res = filterByRole('security', partial)
    // равные ключи → стабильный порядок исходного массива, без NaN-скачков
    expect(res.map((i) => i.id)).toEqual(['x', 'y'])
  })

  it('не мутирует входной массив', () => {
    const copy = [...items]
    filterByRole('security', items)
    expect(items).toEqual(copy)
  })

  it('пустой вход → пустой выход', () => {
    expect(filterByRole('security', [])).toEqual([])
  })
})

// ── markerOptionsForRole (карта) ──────────────────────────────────────────────
describe('markerOptionsForRole', () => {
  it('Логист: только статус online/offline, без severity-цвета', () => {
    expect(markerOptionsForRole('logist')).toEqual({
      colorBy: 'status',
      emphasizeVideo: false,
    })
  })

  it('Диспетчер: цвет по severity', () => {
    expect(markerOptionsForRole('dispatcher')).toEqual({
      colorBy: 'severity',
      emphasizeVideo: false,
    })
  })

  it('Безопасник: severity + акцент на видео', () => {
    expect(markerOptionsForRole('security')).toEqual({
      colorBy: 'severity',
      emphasizeVideo: true,
    })
  })
})

// ── dedupeByUnit (карта/агрегаты) ─────────────────────────────────────────────
describe('dedupeByUnit', () => {
  const u = (
    unit_id: string | null | undefined,
    severity: string | undefined,
    ts: string,
  ) => ({ unit_id, severity, ts }) as Parameters<typeof dedupeByUnit>[0][number]

  it('1 unit_id = 1 объект (берёт наихудший по severity)', () => {
    const res = dedupeByUnit([
      u('U1', 'low', '2026-01-01T10:00:00Z'),
      u('U1', 'critical', '2026-01-01T09:00:00Z'),
      u('U2', 'medium', '2026-01-01T08:00:00Z'),
    ])
    expect(res).toHaveLength(2)
    const byId = Object.fromEntries(res.map((r) => [r.unit_id, r.severity]))
    expect(byId).toEqual({ U1: 'critical', U2: 'medium' })
  })

  it('при равной severity берёт более поздний ts', () => {
    const res = dedupeByUnit([
      u('U1', 'high', '2026-01-01T08:00:00Z'),
      u('U1', 'high', '2026-01-01T12:00:00Z'),
    ])
    expect(res).toHaveLength(1)
    expect(res[0].ts).toBe('2026-01-01T12:00:00Z')
  })

  it('отбрасывает записи с null/undefined/пустым unit_id, не плодит маркеры', () => {
    const res = dedupeByUnit([
      u(null, 'critical', '2026-01-01T10:00:00Z'),
      u(undefined, 'high', '2026-01-01T10:00:00Z'),
      u('', 'high', '2026-01-01T10:00:00Z'),
      u('U1', 'low', '2026-01-01T10:00:00Z'),
    ])
    expect(res.map((r) => r.unit_id)).toEqual(['U1'])
  })

  it('устойчив к отсутствующей severity (фолбэк-ранг), без NaN', () => {
    const res = dedupeByUnit([
      u('U1', undefined, '2026-01-01T10:00:00Z'),
      u('U1', 'low', '2026-01-01T09:00:00Z'),
    ])
    expect(res).toHaveLength(1)
    expect(res[0].severity).toBe('low') // любой known severity > unknown
  })

  it('пустой вход → пустой выход, не падает', () => {
    expect(dedupeByUnit([])).toEqual([])
  })

  it('не мутирует входной массив', () => {
    const input = [u('U1', 'low', '2026-01-01T10:00:00Z')]
    const copy = [...input]
    dedupeByUnit(input)
    expect(input).toEqual(copy)
  })
})
