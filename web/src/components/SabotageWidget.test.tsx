import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { SABOTAGE_EVENTS } from '@/api/fixtures'

/**
 * f12 · SabotageWidget — виджет детекции саботажа камеры на фикстуре (§7.5 SabotageEvent):
 *  • full: заголовок + счётчик + карточки (оверлей «DMS перекрыта», скорость-улика);
 *  • compact: свёрнутая сводка, «Подробнее» разворачивает карточки;
 *  • действие «Создать заявку» дёргает postAction и фиксирует исход.
 */
vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return { ...actual, getSabotage: vi.fn(), postAction: vi.fn() }
})

import * as client from '@/api/client'
import { SabotageWidget } from './SabotageWidget'

describe('f12 · SabotageWidget', () => {
  beforeEach(() => {
    vi.mocked(client.getSabotage).mockResolvedValue(SABOTAGE_EVENTS)
    vi.mocked(client.postAction).mockResolvedValue({
      incident_id: 'x',
      action: 'create_task',
      comment: '',
      status: 'in_progress',
    })
  })
  afterEach(() => vi.clearAllMocks())

  it('full: заголовок, счётчик и карточки с оверлеем «DMS перекрыта»', async () => {
    render(<SabotageWidget variant="full" />)
    expect(
      await screen.findByText('Камера заблокирована · подозрение на саботаж'),
    ).toBeInTheDocument()
    // Счётчик = числу событий фикстуры
    expect(screen.getByLabelText(`Событий за период: ${SABOTAGE_EVENTS.length}`)).toBeInTheDocument()
    // Оверлей dms_dark + водитель из фикстуры
    expect(screen.getAllByText('DMS перекрыта').length).toBe(SABOTAGE_EVENTS.length)
    expect(screen.getByText('Иванов Алексей Петрович')).toBeInTheDocument()
  })

  it('compact: свёрнутая сводка, «Подробнее» разворачивает карточки', async () => {
    render(<SabotageWidget variant="compact" />)
    await screen.findByText('Камера заблокирована · подозрение на саботаж')
    // В свёрнутом виде кнопок действий ещё нет
    expect(screen.queryByRole('button', { name: 'Создать заявку' })).toBeNull()

    // aria-label перекрывает видимый текст «Подробнее»
    fireEvent.click(screen.getByRole('button', { name: 'Развернуть список саботажа' }))
    expect(screen.getAllByRole('button', { name: 'Создать заявку' }).length).toBeGreaterThanOrEqual(1)
  })

  it('действие «Создать заявку» дёргает postAction и фиксирует исход', async () => {
    render(<SabotageWidget variant="full" />)
    await screen.findByText('Камера заблокирована · подозрение на саботаж')

    fireEvent.click(screen.getAllByRole('button', { name: 'Создать заявку' })[0])
    expect(await screen.findByText('Заявка создана')).toBeInTheDocument()
    expect(client.postAction).toHaveBeenCalledWith(
      expect.objectContaining({ action: 'create_task' }),
    )
  })
})
