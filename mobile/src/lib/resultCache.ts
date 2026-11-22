import type { CheckResult } from '@/api/types'

const results = new Map<string, CheckResult>()

export function setCachedResult(result: CheckResult): void {
  results.set(result.check_id, result)
}

export function getCachedResult(checkId: string): CheckResult | undefined {
  return results.get(checkId)
}
