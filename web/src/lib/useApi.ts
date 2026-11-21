import { useEffect, useState } from 'react'

import { ApiError } from '../api/client'
import { getMessages } from './i18n'

type ApiState<T> = { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; data: T }

export function getErrorText(error: unknown): string {
  return error instanceof ApiError ? error.message : getMessages().errors.generic
}

/** Loads data once per `key`; `initialData` skips the request (e.g. a result passed via navigation). */
export function useApi<T>(key: string, fetcher: () => Promise<T>, initialData?: T): ApiState<T> {
  const [state, setState] = useState<ApiState<T>>(
    initialData === undefined ? { status: 'loading' } : { status: 'ready', data: initialData },
  )

  useEffect(() => {
    if (initialData !== undefined) return
    let isCurrent = true
    setState({ status: 'loading' })
    fetcher()
      .then((data) => isCurrent && setState({ status: 'ready', data }))
      .catch((error: unknown) => isCurrent && setState({ status: 'error', message: getErrorText(error) }))
    return () => {
      isCurrent = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload only when the key changes
  }, [key])

  return state
}
