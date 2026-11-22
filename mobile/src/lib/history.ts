import AsyncStorage from '@react-native-async-storage/async-storage'

import type { CheckResult, Verdict } from '@/api/types'

const HISTORY_KEY = 'prawdowid.history'
const MAX_HISTORY = 30

/** Only ids and a short label stay on the device (CONCEPT §7.6). */
export type HistoryEntry = {
  checkId: string
  label: string
  createdAt: string
  verdicts: Verdict[]
  status: CheckResult['status']
}

export async function getHistory(): Promise<HistoryEntry[]> {
  try {
    const parsed: unknown = JSON.parse((await AsyncStorage.getItem(HISTORY_KEY)) ?? '[]')
    return Array.isArray(parsed) ? (parsed as HistoryEntry[]) : []
  } catch {
    return []
  }
}

export async function addHistoryEntry(result: CheckResult, label: string): Promise<void> {
  const entry: HistoryEntry = {
    checkId: result.check_id,
    label: label.slice(0, 140),
    createdAt: new Date().toISOString(),
    verdicts: result.claims.map((claim) => claim.verdict),
    status: result.status,
  }
  const rest = (await getHistory()).filter((item) => item.checkId !== entry.checkId)
  await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify([entry, ...rest].slice(0, MAX_HISTORY)))
}

export async function clearHistory(): Promise<void> {
  await AsyncStorage.removeItem(HISTORY_KEY)
}
