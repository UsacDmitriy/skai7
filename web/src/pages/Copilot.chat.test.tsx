import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { CopilotMessage } from '@/api/types'

/**
 * f17 · Copilot (`/copilot`) — диалоговый AI-копилот (§8.4, идея #13):
 *  • idle: empty-state с подсказками; пустой ввод заблокирован (кнопка disabled);
 *  • ввод → ответ ассистента на фикстуре + «Связанные данные» со ссылкой на экран;
 *  • ошибка ответа → плашка ошибки + «Повторить» (retry повторяет запрос).
 *
 * `detectLang` оставляем настоящим (язык реплики), `sendCopilotMessage` мокаем —
 * детерминированно, без сети.
 */
vi.mock('@/api/copilot', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/copilot')>()
  return { ...actual, sendCopilotMessage: vi.fn() }
})

import * as copilot from '@/api/copilot'
import Copilot from './Copilot'

const REPLY: CopilotMessage = {
  role: 'assistant',
  text: 'Топ-3 по риску: Иванов, Сидоров, Козлов.',
  lang: 'ru',
  tool_calls: [{ name: 'get_zones', args: { kind: 'incident' } }],
  data: { zones: ['zone-inc-01'] },
}

function renderCopilot() {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Copilot />
    </MemoryRouter>,
  )
}

/** Печатает вопрос в поле ввода и жмёт «Отправить». */
function ask(text: string) {
  fireEvent.change(screen.getByRole('textbox'), { target: { value: text } })
  fireEvent.click(screen.getByRole('button', { name: 'Отправить' }))
}

describe('f17 · Copilot', () => {
  beforeEach(() => {
    vi.mocked(copilot.sendCopilotMessage).mockResolvedValue(REPLY)
  })
  afterEach(() => vi.clearAllMocks())

  it('idle: empty-state с подсказками, кнопка отправки заблокирована при пустом вводе', () => {
    renderCopilot()
    expect(screen.getByText('Чем помочь?')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Отправить' })).toBeDisabled()
  })

  it('пустой/пробельный ввод не отправляется (кнопка остаётся disabled)', () => {
    renderCopilot()
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '   ' } })
    expect(screen.getByRole('button', { name: 'Отправить' })).toBeDisabled()
    expect(copilot.sendCopilotMessage).not.toHaveBeenCalled()
  })

  it('ввод → ответ ассистента + «Связанные данные» со ссылкой на экран', async () => {
    renderCopilot()
    ask('Покажи топ-3 водителей по риску')

    // Реплика пользователя в ленте.
    expect(screen.getByText('Покажи топ-3 водителей по риску')).toBeInTheDocument()
    // Ответ ассистента (после резолва промиса).
    expect(await screen.findByText(REPLY.text)).toBeInTheDocument()
    expect(copilot.sendCopilotMessage).toHaveBeenCalledWith('Покажи топ-3 водителей по риску')
    // tool_call get_zones → ссылка-дрилдаун «Зоны на карте» (→ /monitor).
    const link = screen.getByRole('link', { name: /Зоны на карте/ })
    expect(link).toHaveAttribute('href', '/monitor')
  })

  it('ошибка ответа → плашка ошибки + «Повторить»; retry повторяет запрос', async () => {
    vi.mocked(copilot.sendCopilotMessage)
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValueOnce(REPLY)

    renderCopilot()
    ask('Покажи риск')

    // Плашка ошибки (ru-фолбэк сети) + кнопка повтора.
    expect(await screen.findByRole('alert')).toHaveTextContent('Не удалось получить ответ')
    const retry = screen.getByRole('button', { name: 'Повторить' })

    fireEvent.click(retry)
    // Повтор того же запроса → приходит успешный ответ, ошибка уходит.
    expect(await screen.findByText(REPLY.text)).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
    expect(copilot.sendCopilotMessage).toHaveBeenCalledTimes(2)
  })

  it('retry не дублирует сообщение пользователя (регресс)', async () => {
    vi.mocked(copilot.sendCopilotMessage)
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValueOnce(REPLY)

    renderCopilot()
    ask('Проверка дубля')

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Повторить' }))
    expect(await screen.findByText(REPLY.text)).toBeInTheDocument()

    // До фикса retry повторно добавлял user-бабл → было бы 2.
    expect(screen.getAllByText('Проверка дубля')).toHaveLength(1)
    expect(copilot.sendCopilotMessage).toHaveBeenCalledTimes(2)
  })
})
