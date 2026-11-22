import { ERRORS } from '@/constants/labels'
import { getSessionId } from '@/lib/session'
import { getServerUrl } from '@/lib/settings'

import type { CheckInput, CheckResult } from './types'

const CHECK_TIMEOUT_MS = 240_000
const DEFAULT_TIMEOUT_MS = 20_000

export class ApiError extends Error {}

function getErrorMessage(status: number): string {
  if (status === 404) return ERRORS.notFound
  if (status === 422) return ERRORS.invalid
  return ERRORS.unavailable
}

async function getJson<T>(path: string, init: RequestInit = {}, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${await getServerUrl()}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init.headers },
      signal: AbortSignal.timeout(timeoutMs),
    })
  } catch {
    throw new ApiError(ERRORS.offline)
  }
  if (!response.ok) throw new ApiError(getErrorMessage(response.status))
  return (await response.json()) as T
}

export async function postCheck(input: CheckInput): Promise<CheckResult> {
  const request = { channel: 'mobile', session_id: await getSessionId(), input, language: 'pl' }
  return getJson('/v1/checks', { method: 'POST', body: JSON.stringify(request) }, CHECK_TIMEOUT_MS)
}

export function getCheck(checkId: string): Promise<CheckResult> {
  return getJson(`/v1/checks/${encodeURIComponent(checkId)}`)
}

export async function deleteSession(): Promise<void> {
  await getJson(`/v1/sessions/${encodeURIComponent(await getSessionId())}`, { method: 'DELETE' })
}
