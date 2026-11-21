import type { CheckResult, Verdict } from '../api/types'

const SESSION_KEY = 'prawdowid.session'
const HISTORY_KEY = 'prawdowid.history'
const MAX_HISTORY = 30

export type HistoryEntry = {
  checkId: string
  label: string
  createdAt: string
  verdicts: Verdict[]
  status: CheckResult['status']
}

function readStorage(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function writeStorage(key: string, value: string | null): void {
  try {
    if (value === null) localStorage.removeItem(key)
    else localStorage.setItem(key, value)
  } catch {
    // Storage can be unavailable (private mode); the app works without it.
  }
}

function getNewSessionId(): string {
  return `web-${crypto.randomUUID().replaceAll('-', '')}`
}

export function getSessionId(): string {
  const existing = readStorage(SESSION_KEY)
  if (existing) return existing
  const created = getNewSessionId()
  writeStorage(SESSION_KEY, created)
  return created
}

export function getHistory(): HistoryEntry[] {
  try {
    const parsed: unknown = JSON.parse(readStorage(HISTORY_KEY) ?? '[]')
    return Array.isArray(parsed) ? (parsed as HistoryEntry[]) : []
  } catch {
    return []
  }
}

export function addHistoryEntry(result: CheckResult, label: string): void {
  const entry: HistoryEntry = {
    checkId: result.check_id,
    label: label.slice(0, 140),
    createdAt: new Date().toISOString(),
    verdicts: result.claims.map((claim) => claim.verdict),
    status: result.status,
  }
  const rest = getHistory().filter((item) => item.checkId !== entry.checkId)
  writeStorage(HISTORY_KEY, JSON.stringify([entry, ...rest].slice(0, MAX_HISTORY)))
}

export function clearLocalData(): void {
  writeStorage(HISTORY_KEY, null)
  writeStorage(SESSION_KEY, null)
}
