import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import FuelCard from './FuelCard'

/**
 * w3-15 · Карточка топлива против §9.2/§9.4 (режим фикстур, без сети).
 *  • таблица сверки транзакция↔датчик + список заправок/сливов рендерятся;
 *  • `recon_status`-бейдж окрашен по токену severity (review → warning);
 *  • неизвестный ТС → 404-плашка «ТС не найдено» (не белый экран).
 *
 * `getFuel(plate)` берёт данные из фикстур f3 (`VITE_USE_FIXTURES=true`).
 */

function renderFuel(plate: string) {
  return render(
    <MemoryRouter
      initialEntries={[`/fleet-health/fuel/${plate}`]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/fleet-health/fuel/:plate" element={<FuelCard />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('FuelCard · карточка топлива', () => {
  it('таблица сверки + список заправок рендерятся; recon-бейдж окрашен', async () => {
    renderFuel('А144ЕВ193') // recon_status = review

    // Бейдж сверки окрашен токеном warning (review → medium, §9.2).
    const badge = await screen.findByText('Требует проверки')
    expect(badge).toHaveClass('bg-warning-bg')

    // Таблица сверки карта ↔ датчик.
    expect(screen.getByText('Сверка карта ↔ датчик')).toBeInTheDocument()
    expect(screen.getByText('Расхождение объёма >20 л и времени >25 мин')).toBeInTheDocument()

    // Список заправок/сливов.
    expect(screen.getByText('Заправки и сливы')).toBeInTheDocument()
    expect(screen.getByText('Заправка')).toBeInTheDocument()
    expect(screen.getByText('Слив')).toBeInTheDocument()
  })

  it('404 → плашка «ТС не найдено» (не белый экран)', async () => {
    renderFuel('НЕТ-ТАКОГО-999')

    expect(await screen.findByText('ТС не найдено')).toBeInTheDocument()
    // Не белый экран: есть навигационный выход.
    expect(screen.getByRole('button', { name: /Назад/ })).toBeInTheDocument()
  })
})
