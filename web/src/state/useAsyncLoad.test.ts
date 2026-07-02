import { renderHook, act, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { useAsyncLoad } from './useAsyncLoad'

describe('useAsyncLoad', () => {
  it('успех', async () => {
    const fetcher = () => Promise.resolve({ x: 1 })
    const { result } = renderHook(() => useAsyncLoad<{ x: number }>(fetcher))

    expect(result.current.state).toBe('loading')
    await waitFor(() => expect(result.current.state).toBe('ready'))
    expect(result.current.data).toEqual({ x: 1 })
    expect(result.current.error).toBeNull()
  })

  it('ошибка', async () => {
    const fetcher = () => Promise.reject(new Error('boom'))
    const { result } = renderHook(() => useAsyncLoad<string>(fetcher))

    await waitFor(() => expect(result.current.state).toBe('error'))
    expect(result.current.error).toBe('boom')
    expect(result.current.data).toBeNull()
  })

  it('errorMessage-фолбэк для не-Error', async () => {
    const fetcher = () => Promise.reject('str')
    const { result } = renderHook(() =>
      useAsyncLoad<string>(fetcher, { errorMessage: 'custom error' }),
    )

    await waitFor(() => expect(result.current.state).toBe('error'))
    expect(result.current.error).toBe('custom error')
    expect(result.current.data).toBeNull()
  })

  it('reload перезапускает', async () => {
    const fetcher = vi.fn(() => Promise.resolve('a'))
    const { result } = renderHook(() => useAsyncLoad<string>(fetcher))

    await waitFor(() => expect(result.current.state).toBe('ready'))
    act(() => result.current.reload())
    expect(fetcher).toHaveBeenCalledTimes(2)
  })

  it('гонка: устаревший ответ игнорируется', async () => {
    const resolvers: Array<(value: string) => void> = []
    const fetcher = () => new Promise<string>((resolve) => { resolvers.push(resolve) })

    const { result } = renderHook(() => useAsyncLoad<string>(fetcher))
    expect(resolvers.length).toBe(1)

    act(() => result.current.reload())
    expect(resolvers.length).toBe(2)

    act(() => resolvers[1]('new'))
    await waitFor(() => expect(result.current.state).toBe('ready'))
    expect(result.current.data).toBe('new')

    // Поздний ответ первого (устаревшего) запроса не должен перезаписать 'new'.
    act(() => resolvers[0]('old'))
    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(result.current.data).toBe('new')
  })
})
