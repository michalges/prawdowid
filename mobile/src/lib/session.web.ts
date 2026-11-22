const SESSION_KEY = 'prawdowid.session'

/** Web build (Expo web): secure storage isn't available, so the session id lives in localStorage like the web app. */
export async function getSessionId(): Promise<string> {
  const existing = localStorage.getItem(SESSION_KEY)
  if (existing) return existing
  const created = `mobile-${crypto.randomUUID().replaceAll('-', '')}`
  localStorage.setItem(SESSION_KEY, created)
  return created
}

export async function clearSessionId(): Promise<void> {
  localStorage.removeItem(SESSION_KEY)
}
