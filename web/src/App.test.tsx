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
  it('мёртвый путь /live → ComingSoon с описанием секции и пилюлей «Волна 4», не generic', async () => {
    renderAppAt('/live')

    // Описание конкретной секции (а не generic «Раздел в разработке»).
    expect(await screen.findByText('Видеопоток с бортовых камер — стриминг.')).toBeInTheDocument()
    // Пилюля «Скоро · Волна 4».
    expect(screen.getByText(/Скоро · Волна 4/)).toBeInTheDocument()
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
