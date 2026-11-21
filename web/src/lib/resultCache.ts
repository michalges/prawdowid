import { getCheck } from '../api/client'
import type { CheckResult } from '../api/types'

export type CachedResult = { result: CheckResult; label: string | null }

const results = new Map<string, CachedResult>()

export function setCachedResult(result: CheckResult, label: string): void {
  results.set(result.check_id, { result, label })
}

/** A just-created result is shown without a second request; shared links load from the API. */
export async function getResult(checkId: string): Promise<CachedResult> {
  return results.get(checkId) ?? { result: await getCheck(checkId), label: null }
}
