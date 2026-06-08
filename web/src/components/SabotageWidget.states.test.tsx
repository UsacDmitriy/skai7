import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { SABOTAGE_EVENTS } from '@/api/fixtures'

/**
 * f12 · SabotageWidget — состояния:
 *  • loading → скелет; empty → «Саботаж не обнаружен»; error → «Повторить» (ретрай).
 */
vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return { ...actual, getSabotage: vi.fn(), postAction: vi.fn() }
})

import * as client from '@/api/client'
import { SabotageWidget } from './SabotageWidget'

describe('f12 · SabotageWidget — состояния', () => {
  afterEach(() => vi.mocked(client.getSabotage).mockReset())

  it('loading: скелет вместо белого экрана', () => {
    vi.mocked(client.getSabotage).mockReturnValue(new Promise(() => {}))
    const { container } = render(<SabotageWidget variant="full" />)
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('empty: «Саботаж не обнаружен»', async () => {
    vi.mocked(client.getSabotage).mockResolvedValue([])
    render(<SabotageWidget variant="full" />)
    expect(await screen.findByText('Саботаж не обнаружен')).toBeInTheDocument()
  })

  it('error: плашка + «Повторить» (ретрай повторно дёргает клиент)', async () => {
    vi.mocked(client.getSabotage).mockRejectedValue(new Error('сервис саботажа упал'))
    render(<SabotageWidget variant="compact" />)
    expect(await screen.findByText('сервис саботажа упал')).toBeInTheDocument()
    const retry = screen.getByRole('button', { name: /Повторить/ })

    vi.mocked(client.getSabotage).mockResolvedValue(SABOTAGE_EVENTS)
    fireEvent.click(retry)
    await waitFor(() => expect(vi.mocked(client.getSabotage).mock.calls.length).toBeGreaterThan(1))
  })
})
