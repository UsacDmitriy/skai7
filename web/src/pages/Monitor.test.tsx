import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { IncidentSummary } from '@/api/types'
import { RoleProvider } from '@/state/role'

/**
 * f6 · Monitor — гейт Check t3: дедупликация ТС «1 unit_id = 1 маркер».
 * Лента из N алярмов с повторяющимися госномерами → ровно по одному маркеру на ТС
 * (карта `unit_id` = госномер, см. Monitor.buildUnits). Leaflet/виджеты мокаем —
 * проверяем именно правило дедупа, а не отрисовку карты.
 */

// Карта-заглушка: считаем маркеры, что реально дошли до слоя.
vi.mock('@/components/map', () => ({
  MapView: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="map">{children}</div>
  ),
  MarkerLayer: ({ units }: { units: Array<{ unit_id: string }> }) => (
    <div data-testid="marker-layer" data-count={units.length}>
      {units.map((u) => (
        <div key={u.unit_id} data-testid="marker" data-unit={u.unit_id} />
      ))}
    </div>
  ),
  RoleToggle: () => <div data-testid="role-toggle" />,
}))

vi.mock('@/components/SabotageWidget', () => ({
  SabotageWidget: () => <div data-testid="sabotage" />,
}))

const listIncidents = vi.fn()
vi.mock('@/api/client', () => ({
  listIncidents: () => listIncidents(),
}))

// Импорт страницы — после vi.mock (hoisted), чтобы подхватились заглушки.
import Monitor from './Monitor'

const mk = (over: Partial<IncidentSummary>): IncidentSummary => ({
  id: 'inc-x',
  alarm_type: 'OVERSPEED',
  alarm_code: 'OVERSPEED',
  alarm_label_ru: 'Превышение скорости',
  source: 'TELEMATICS',
  severity: 'high',
  risk_level: 'high',
  risk_score: 50,
  ts: '2026-04-02T10:00:00',
  vehicle_plate: 'А111АА 77',
  driver: 'Тест Водитель',
  vehicle_model: 'ГАЗон NEXT',
  speed_kmh: 80,
  lat: 55.75,
  lon: 37.61,
  address: 'ул. Тестовая, 1',
  video_available: true,
  status: 'active',
  ...over,
})

// 5 алярмов на 3 разных госномера (2 + 2 + 1).
const INCIDENTS: IncidentSummary[] = [
  mk({ id: 'a1', vehicle_plate: 'А111АА 77', severity: 'low', ts: '2026-04-02T10:00:00' }),
  mk({ id: 'a2', vehicle_plate: 'А111АА 77', severity: 'critical', ts: '2026-04-02T11:00:00' }),
  mk({ id: 'b1', vehicle_plate: 'В222ВВ 97', severity: 'medium', ts: '2026-04-02T09:00:00' }),
  mk({ id: 'b2', vehicle_plate: 'В222ВВ 97', severity: 'high', ts: '2026-04-02T12:00:00' }),
  mk({ id: 'c1', vehicle_plate: 'С333СС 99', severity: 'high', ts: '2026-04-02T08:00:00' }),
]

function renderMonitor() {
  return render(
    <RoleProvider>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Monitor />
      </MemoryRouter>
    </RoleProvider>,
  )
}

describe('Monitor · дедупликация ТС', () => {
  beforeEach(() => {
    localStorage.clear() // дефолтная роль «Диспетчер» (полный список)
    listIncidents.mockResolvedValue(INCIDENTS)
  })

  afterEach(() => {
    listIncidents.mockReset()
  })

  it('5 алярмов на 3 госномера → 3 маркера (1 unit_id = 1 маркер)', async () => {
    renderMonitor()

    const markers = await screen.findAllByTestId('marker')
    expect(markers).toHaveLength(3)

    // Каждый госномер встречается ровно один раз.
    const units = markers.map((m) => m.getAttribute('data-unit'))
    expect(new Set(units)).toEqual(new Set(['А111АА 77', 'В222ВВ 97', 'С333СС 99']))
    expect(units).toHaveLength(new Set(units).size)
  })

  it('лента показывает все алярмы (5), маркеров меньше — это и есть дедуп', async () => {
    renderMonitor()

    await screen.findByTestId('marker-layer')
    // Счётчик «Активные алярмы (N)» — все алярмы, не дедуплицированные ТС.
    expect(screen.getByText('(5)')).toBeInTheDocument()
    expect(screen.getByTestId('marker-layer')).toHaveAttribute('data-count', '3')
  })
})

describe('Monitor · роль «Логист» скрывает DMS-слой', () => {
  beforeEach(() => {
    localStorage.setItem('skai.role', 'logist')
  })
  afterEach(() => {
    localStorage.clear()
    listIncidents.mockReset()
  })

  it('DMS-алармы не попадают на карту и в ленту под ролью Логист', async () => {
    listIncidents.mockResolvedValue([
      mk({ id: 'dms', vehicle_plate: 'D111АА 77', source: 'DMS', severity: 'critical' }),
      mk({ id: 'tel', vehicle_plate: 'T222ВВ 97', source: 'TELEMATICS', severity: 'high' }),
      mk({ id: 'adas', vehicle_plate: 'E333СС 99', source: 'ADAS', severity: 'medium' }),
    ])
    renderMonitor()

    await screen.findByTestId('marker-layer')
    const units = screen.getAllByTestId('marker').map((m) => m.getAttribute('data-unit'))
    expect(units).not.toContain('D111АА 77') // DMS-слой скрыт для логиста
    expect(units).toEqual(expect.arrayContaining(['T222ВВ 97', 'E333СС 99']))
    expect(screen.getByText('(2)')).toBeInTheDocument()
  })
})
