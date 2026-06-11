import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ConsistencyPanel } from './ConsistencyPanel'
import { CONSISTENCY_REPORT } from '../../api/fixtures'

/**
 * f25 · ConsistencyPanel — светофор по 7 проверкам + сводные доли (§10.2).
 *  • рендер на фикстуре: 7 строк, заголовки, сводные доли, статусы словами;
 *  • пустой/ошибочный ответ (null) → заглушка «нет данных», без краша.
 */

describe('f25 · ConsistencyPanel', () => {
  it('фикстура: 7 проверок со светофором словами + сводные доли', () => {
    render(<ConsistencyPanel data={CONSISTENCY_REPORT} />)

    // Заголовки проверок видны (по одной строке на проверку).
    expect(screen.getByText('Дубли терминалов на ТС')).toBeInTheDocument()
    expect(screen.getByText('Расхождение скоростей')).toBeInTheDocument()

    // Светофор не только цветом — статус выведен словом (a11y).
    expect(screen.getAllByText('Внимание').length).toBeGreaterThan(0)
    expect(screen.getByText('Проблема')).toBeInTheDocument()
    expect(screen.getAllByText('В норме').length).toBeGreaterThan(0)

    // Сводные доли — подписи присутствуют.
    expect(screen.getByText('Доказательная база')).toBeInTheDocument()
    expect(screen.getByText('Согласие скоростей')).toBeInTheDocument()
  })

  it('null (ошибка/нет ответа) → заглушка, без краша', () => {
    render(<ConsistencyPanel data={null} />)
    expect(screen.getByText('Нет данных консистентности.')).toBeInTheDocument()
  })

  it('пустой список проверок → заглушка', () => {
    render(
      <ConsistencyPanel
        data={{ checks: [], evidence_rate: 1, speed_agreement_rate: 1, generated_at_source: 'duckdb' }}
      />,
    )
    expect(screen.getByText('Нет данных консистентности.')).toBeInTheDocument()
  })
})
