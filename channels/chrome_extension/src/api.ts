import { ERRORS } from './labels.js'
import { getSessionId } from './settings.js'
import type { CheckInput, CheckResult } from './types.js'

const CHECK_TIMEOUT_MS = 240_000

export class ApiError extends Error {}

async function getResponse(url: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init)
  } catch (error) {
    if (error instanceof DOMException && error.name === 'TimeoutError') throw new ApiError(ERRORS.timeout)
    throw new ApiError(ERRORS.offline)
  }
}

export async function postCheck(serverUrl: string, input: CheckInput): Promise<CheckResult> {
  const response = await getResponse(`${serverUrl}/v1/checks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ channel: 'browser_extension', session_id: await getSessionId(), input, language: 'pl' }),
    signal: AbortSignal.timeout(CHECK_TIMEOUT_MS),
  })
  if (response.status === 422) throw new ApiError(ERRORS.invalid)
  if (!response.ok) throw new ApiError(ERRORS.unavailable)
  return (await response.json()) as CheckResult
}

export async function deleteSession(serverUrl: string): Promise<void> {
  const sessionId = encodeURIComponent(await getSessionId())
  const response = await getResponse(`${serverUrl}/v1/sessions/${sessionId}`, { method: 'DELETE' })
  if (!response.ok) throw new ApiError(ERRORS.unavailable)
}

export async function isServerHealthy(serverUrl: string): Promise<boolean> {
  try {
    const response = await fetch(`${serverUrl}/health`, { signal: AbortSignal.timeout(10_000) })
    return response.ok
  } catch {
    return false
  }
}
