export const DEFAULT_SERVER_URL = 'http://localhost:5173'

const SERVER_URL_KEY = 'serverUrl'
const SESSION_ID_KEY = 'sessionId'

export function getNormalizedServerUrl(rawUrl: string): string | null {
  try {
    const parsed = new URL(rawUrl.trim())
    if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') return null
    return parsed.origin + parsed.pathname.replace(/\/+$/, '')
  } catch {
    return null
  }
}

export function getOriginPattern(serverUrl: string): string {
  return `${new URL(serverUrl).origin}/*`
}

export async function getServerUrl(): Promise<string> {
  const stored = await chrome.storage.sync.get(SERVER_URL_KEY)
  const value = stored[SERVER_URL_KEY]
  return typeof value === 'string' ? value : DEFAULT_SERVER_URL
}

export async function setServerUrl(serverUrl: string): Promise<void> {
  await chrome.storage.sync.set({ [SERVER_URL_KEY]: serverUrl })
}

/** Pseudonymous and per-install, like the web channel's `web-…` session. */
export async function getSessionId(): Promise<string> {
  const stored = await chrome.storage.local.get(SESSION_ID_KEY)
  const existing = stored[SESSION_ID_KEY]
  if (typeof existing === 'string') return existing
  const created = `ext-${crypto.randomUUID().replaceAll('-', '')}`
  await chrome.storage.local.set({ [SESSION_ID_KEY]: created })
  return created
}

export async function clearSessionId(): Promise<void> {
  await chrome.storage.local.remove(SESSION_ID_KEY)
}
