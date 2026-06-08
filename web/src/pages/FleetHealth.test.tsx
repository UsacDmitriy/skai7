import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { FLEET_HEALTH } from '@/api/fixtures'

/**
 * w3-15 · Хаб «Здоровье парка» против §9.0/§9.4 (режим фикстур, без сети).
 *  • ростер = объединение доменов; баннер покрытия «10 · 7 · 5 · 2»;
 *  • «—» для отсутствующих у ТС доменов (фича, не баг);
 *  • 2 строки помечены «в видеопарке»;
 *  • клик по строке → самый «богатый» домен (fuel → sensor → REB);
 *  • состояния loading/empty/error (экран вне scope w3-4 — покрытие за w3-15).
 *
 * `getFleetHealth` мокаем, чтобы прогнать happy/empty/error; happy-данные —
 * та же фикстура f3 `FLEET_HEALTH`, что и в `VITE_USE_FIXTURES`-режиме.
 */
vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return { ...actual, getFleetHealth: vi.fn() }
})

import * as client from '@/api/client'
import FleetHealth from './FleetHealth'

// Зонд текущего пути — наблюдаем навигацию по клику строки, не завязываясь на экраны-цели.
function LocationProbe() {
  const loc = useLocation()
  return <div data-testid="loc">{loc.pathname}</div>
}

function renderHub() {
  return render(
    <MemoryRouter
      initialEntries={['/fleet-health']}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <FleetHealth />
      <LocationProbe />
    </MemoryRouter>,
  )
}

describe('FleetHealth · хаб «Здоровье парка»', () => {
  beforeEach(() => {
    vi.mocked(client.getFleetHealth).mockResolvedValue(FLEET_HEALTH)
  })
  afterEach(() => {
    vi.mocked(client.getFleetHealth).mockReset()
  })

  it('ростер рендерит объединение + баннер покрытия «10 · 7 · 5 · 2»', async () => {
    renderHub()

    // Баннер покрытия (disjoint-популяции §9.0) — обязателен.
    const banner = (await screen.findByText('Покрытие парка')).closest('div') as HTMLElement
    expect(within(banner).getByText(/Топливо/)).toBeInTheDocument()
    expect(within(banner).getByText(/Сенсоры/)).toBeInTheDocument()
    expect(within(banner).getByText(/Навигация/)).toBeInTheDocument()
    expect(within(banner).getByText('10')).toBeInTheDocument()
    expect(within(banner).getByText('7')).toBeInTheDocument()
    expect(within(banner).getByText('5')).toBeInTheDocument()
    expect(within(banner).getByText('2')).toBeInTheDocument()

    // Ростер: строки объединения по нормализованному госномеру.
    expect(screen.getByText('КамАЗ-65115')).toBeInTheDocument()
    expect(screen.getByText('КамАЗ-43118 · Т671КР31')).toBeInTheDocument()
    expect(screen.getByText('МАЗ-6312 · О802УЕ198')).toBeInTheDocument()
  })

  it('у ТС без домена ячейка = «—» (особенность фрагментированного парка)', async () => {
    renderHub()
    await screen.findByText('Покрытие парка')

    // А144ЕВ193 (КамАЗ-65115) — только топливо: сенсоры/online/навигация = «—».
    const row = screen.getByText('КамАЗ-65115').closest('tr') as HTMLElement
    expect(within(row).getAllByText('—').length).toBeGreaterThanOrEqual(1)
    // У строки есть реальное топливо (не «—» во всех ячейках).
    expect(within(row).getByText('+22,5 л')).toBeInTheDocument()
  })

  it('ровно 2 строки помечены «в видеопарке»', async () => {
    renderHub()
    await screen.findByText('Покрытие парка')

    // getAllByRole('row') = шапка + строки данных; бейдж только в строках ТС.
    const tagged = screen.getAllByRole('row').filter((r) => within(r).queryByText('в видеопарке'))
    expect(tagged).toHaveLength(2)
  })

  it('клик по строке с топливом → /fleet-health/fuel/:plate', async () => {
    renderHub()
    await screen.findByText('Покрытие парка')

    fireEvent.click(screen.getByText('КамАЗ-65115')) // А144ЕВ193, has_fuel
    await waitFor(() =>
      expect(screen.getByTestId('loc').textContent).toMatch(/^\/fleet-health\/fuel\//),
    )
  })

  it('клик по строке с сенсорами → /fleet-health/sensors/:plate', async () => {
    renderHub()
    await screen.findByText('Покрытие парка')

    fireEvent.click(screen.getByText('КамАЗ-43118 · Т671КР31')) // has_sensors
    await waitFor(() =>
      expect(screen.getByTestId('loc').textContent).toMatch(/^\/fleet-health\/sensors\//),
    )
  })

  it('клик по строке только с навигацией → /reb/:id (самый «богатый» доступный домен)', async () => {
    renderHub()
    await screen.findByText('Покрытие парка')

    fireEvent.click(screen.getByText('МАЗ-6312 · О802УЕ198')) // has_nav + reb_link_id
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toMatch(/^\/reb\//))
  })

  it('сортировка колонок переупорядочивает ростер (asc/desc) без потери строк', async () => {
    renderHub()
    await screen.findByText('Покрытие парка')

    // Сортировка по «ТС» (vehicle sortValue), затем по топливной дельте (asc→desc).
    fireEvent.click(screen.getByRole('button', { name: 'ТС' }))
    fireEvent.click(screen.getByRole('button', { name: /Топливо Δ ЗИС/ }))
    fireEvent.click(screen.getByRole('button', { name: /Топливо Δ ЗИС/ }))

    // Ростер уцелел после сортировки.
    expect(screen.getByText('КамАЗ-65115')).toBeInTheDocument()
    expect(screen.getByText('МАЗ-6312 · О802УЕ198')).toBeInTheDocument()
  })

  it('empty: нет ТС с телеметрией → дружелюбная плашка (не белый экран)', async () => {
    vi.mocked(client.getFleetHealth).mockResolvedValue({
      coverage: { fuel: 0, sensors: 0, navigation: 0, in_video_fleet: 0 },
      rows: [],
    })
    renderHub()

    expect(await screen.findByText('Нет ТС с телематическими данными')).toBeInTheDocument()
  })

  it('error: сбой загрузки → плашка ошибки + «Повторить» перезапрашивает', async () => {
    const { ApiError } = await import('@/api/client')
    vi.mocked(client.getFleetHealth).mockRejectedValue(new ApiError(500, 'boom'))
    renderHub()

    const retry = await screen.findByRole('button', { name: /Повторить/ })
    expect(retry).toBeInTheDocument()

    // Клик «Повторить» снова дёргает загрузку (вторая попытка тоже падает).
    fireEvent.click(retry)
    await waitFor(() =>
      expect(vi.mocked(client.getFleetHealth).mock.calls.length).toBeGreaterThanOrEqual(2),
    )
  })
})
