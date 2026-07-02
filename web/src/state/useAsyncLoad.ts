import { useCallback, useEffect, useRef, useState } from 'react'

/** Состояние асинхронной загрузки. */
export type AsyncLoadState = 'loading' | 'ready' | 'error'

/** Результат хука useAsyncLoad. */
export interface AsyncLoad<T> {
  state: AsyncLoadState
  data: T | null
  error: string | null
  reload: () => void
}

/**
 * Асинхронная загрузка с защитой от гонок и setState-после-unmount.
 *
 * Механизм — счётчик запросов `reqRef`:
 *  • каждый запуск (`run`) берёт номер `my = ++reqRef.current`;
 *  • в then/catch результат применяется только если `reqRef.current === my`;
 *  • cleanup эффекта (unmount / смена deps) делает `reqRef.current++`, тем самым
 *    инвалидируя in-flight запрос — один механизм закрывает и гонку, и unmount.
 *
 * `fetcherRef` обновляется каждый рендер: эффект не пересоздаётся, но вызывается
 * актуальный fetcher. Для параметрических загрузок передавайте `deps` (напр. [id]).
 */
export function useAsyncLoad<T>(
  fetcher: () => Promise<T>,
  options?: { errorMessage?: string; deps?: unknown[] },
): AsyncLoad<T> {
  const { errorMessage = 'Ошибка загрузки', deps = [] } = options ?? {}

  const [state, setState] = useState<AsyncLoadState>('loading')
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reqRef = useRef(0)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const run = useCallback(() => {
    const my = ++reqRef.current
    setState('loading')
    setError(null)
    fetcherRef
      .current()
      .then((d) => {
        if (reqRef.current === my) {
          setData(d)
          setState('ready')
        }
      })
      .catch((e: unknown) => {
        if (reqRef.current === my) {
          setError(e instanceof Error ? e.message : errorMessage)
          setState('error')
        }
      })
  }, [errorMessage])

  /* eslint-disable react-hooks/exhaustive-deps */
  useEffect(() => {
    run()
    return () => {
      reqRef.current++
    }
  }, [run, ...deps])
  /* eslint-enable react-hooks/exhaustive-deps */

  return { state, data, error, reload: run }
}
