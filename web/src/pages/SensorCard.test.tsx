import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import SensorCard from './SensorCard'

/**
 * w3-15 · Карточка сенсоров против §9.2/§9.4/§9.5 (режим фикстур, без сети).
 *  • спарклайн дневного пробега ровно из 7 точек (НЕ сырые 959k graph_points);
 *  • `online_status="stale"` → нейтральный бейдж (не ошибка, §9.5);
 *  • `distance_gap=null` → «нет данных» (не 0);
 *  • в DOM нет утечки сырых `graph_points`/`graph_status`.
 *
 * `getSensors(plate)` берёт данные из фикстур f3 (`VITE_USE_FIXTURES=true`).
 */

function renderSensor(plate: string) {
  return render(
    <MemoryRouter
      initialEntries={[`/fleet-health/sensors/${plate}`]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/fleet-health/sensors/:plate" element={<SensorCard />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('SensorCard · карточка сенсоров', () => {
  it('спарклайн ровно из 7 точек; в DOM нет сырых graph_points', async () => {
    renderSensor('Т671КР31') // online, 7 точек daily_mileage

    const spark = await screen.findByRole('img', { name: /Дневной пробег/ })
    // 7 точек дневного пробега → 7 кругов, а не 959k сырых graph_points (§9.2).
    expect(spark.querySelectorAll('circle')).toHaveLength(7)

    // Анти-регресс: сырые поля телеметрии не утекают в разметку.
    expect(document.body.innerHTML).not.toContain('graph_points')
    expect(document.body.innerHTML).not.toContain('graph_status')
  })

  it('online_status="stale" → нейтральный бейдж (не ошибка)', async () => {
    renderSensor('Х905ОР37') // online_status = stale

    const badge = await screen.findByText(/Stale/)
    // Нейтральная палитра (muted), не критичная/высокая severity.
    expect(badge).toHaveClass('text-muted')
    expect(badge.className).not.toMatch(/critical|high-text/)
  })

  it('distance_gap=null → «нет данных» (не 0)', async () => {
    renderSensor('Х905ОР37') // distance_gap_odometer_minus_gps_km = null

    // KPI разрыва CAN−GPS при null показывает «нет данных».
    expect((await screen.findAllByText('нет данных')).length).toBeGreaterThanOrEqual(1)
  })

  it('online ТС с разрывом показывает числовой CAN−GPS (контраст к null)', async () => {
    renderSensor('Т671КР31') // distance_gap = 540 км

    expect(await screen.findByText('540 км')).toBeInTheDocument()
  })

  it('404 → плашка «ТС не найдено» (не белый экран)', async () => {
    renderSensor('НЕТ-ТАКОГО-999')

    expect(await screen.findByText('ТС не найдено')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Назад/ })).toBeInTheDocument()
  })
})
