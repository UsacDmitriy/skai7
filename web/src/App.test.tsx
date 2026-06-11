import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from './App'

/**
 * w3-15 · Сигнпостинг роутера (§9.4): «мёртвые» пункты меню рендерят `ComingSoon`
 * (название секции + описание + пилюля «Скоро · Волна N»), а НЕ generic
 * «Раздел в разработке». Реальные экраны (`/fleet-health`) рендерятся как есть.
 *
 * `App` монтирует `BrowserRouter`, поэтому путь задаём через `window.history`.
 */

function renderAppAt(path: string) {
  window.history.pushState({}, '', path)
  return render(<App />)
}

describe('App · сигнпостинг ComingSoon (§9.4)', () => {
  it('путь /live → честный сигнпост «Будущее» (нужен live-источник), без обещания волны', async () => {
    renderAppAt('/live')

    // f22: описание честное — датасет исторический, нужен live-источник.
    expect(await screen.findByText(/нужен live-источник/i)).toBeInTheDocument()
    // Пилюля «Будущее» (нейтральный тон), а НЕ «Скоро · Волна N».
    // «Будущее» встречается и в бейдже сайдбара, и в пилюле карточки — оба честны.
    expect(screen.getAllByText('Будущее').length).toBeGreaterThan(0)
    expect(screen.queryByText(/Скоро · Волна/)).not.toBeInTheDocument()
    // Generic-заглушка не используется.
    expect(screen.queryByText('Раздел в разработке')).not.toBeInTheDocument()
  })

  it('/fleet-health → реальный экран (не ComingSoon)', async () => {
    renderAppAt('/fleet-health')

    // Контент реального хаба (баннер покрытия) подтверждает живой экран.
    expect(await screen.findByText('Покрытие парка')).toBeInTheDocument()
    expect(screen.queryByText(/Скоро · Волна/)).not.toBeInTheDocument()
  })
})

describe('App · редиректы дублей (f22, ASSUMPTION — продуктовое решение, не контракт)', () => {
  // ASSUMPTION: цели редиректов выбраны «по сходству»; §7.8/§8 их не мандатируют.
  // Правятся при ревизии (барьер x9+), когда появится промпт-владелец экрана.
  it('/safety → редирект на живой /metrics', async () => {
    renderAppAt('/safety')

    expect(await screen.findByText('Метрики и качество данных')).toBeInTheDocument()
    expect(window.location.pathname).toBe('/metrics')
  })

  it('/dashboards → редирект на живой /metrics', async () => {
    renderAppAt('/dashboards')

    expect(await screen.findByText('Метрики и качество данных')).toBeInTheDocument()
    expect(window.location.pathname).toBe('/metrics')
  })

  it('/quick-report → редирект на живой /copilot', async () => {
    renderAppAt('/quick-report')

    // Реальный экран копилота (заголовок панели) подтверждает живую цель.
    expect(await screen.findByText('AI-копилот')).toBeInTheDocument()
    expect(window.location.pathname).toBe('/copilot')
  })
})
