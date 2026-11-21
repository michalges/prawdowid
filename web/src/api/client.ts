import { getMessages } from '../lib/i18n'
import type { CheckRequest, CheckResult, Health, SourceCatalog } from './types'

const API_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
  }
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError(getMessages().errors.offline, 0)
  }
  if (!response.ok) {
    throw new ApiError(getErrorMessage(response.status), response.status)
  }
  return (await response.json()) as T
}

function getErrorMessage(status: number): string {
  const { errors } = getMessages()
  if (status === 404) return errors.notFound
  if (status === 422) return errors.invalid
  return errors.unavailable
}

export function postCheck(request: CheckRequest): Promise<CheckResult> {
  return getJson('/v1/checks', { method: 'POST', body: JSON.stringify(request) })
}

export function getCheck(checkId: string): Promise<CheckResult> {
  return getJson(`/v1/checks/${encodeURIComponent(checkId)}`)
}

export function getSources(): Promise<SourceCatalog> {
  return getJson('/v1/sources')
}

export function getHealth(): Promise<Health> {
  return getJson('/health')
}

export function deleteSession(sessionId: string): Promise<{ deleted: Record<string, number> }> {
  return getJson(`/v1/sessions/${encodeURIComponent(sessionId)}`, { method: 'DELETE' })
}
