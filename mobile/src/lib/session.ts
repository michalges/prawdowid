import { randomUUID } from 'expo-crypto'
import * as SecureStore from 'expo-secure-store'

const SESSION_KEY = 'prawdowid.session'

/** Random, pseudonymous, kept in secure storage (CONCEPT §7.6). */
export async function getSessionId(): Promise<string> {
  const existing = await SecureStore.getItemAsync(SESSION_KEY)
  if (existing) return existing
  const created = `mobile-${randomUUID().replaceAll('-', '')}`
  await SecureStore.setItemAsync(SESSION_KEY, created)
  return created
}

export async function clearSessionId(): Promise<void> {
  await SecureStore.deleteItemAsync(SESSION_KEY)
}
