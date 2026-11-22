import AsyncStorage from '@react-native-async-storage/async-storage'
import Constants from 'expo-constants'

const SERVER_URL_KEY = 'prawdowid.serverUrl'

export function getDefaultServerUrl(): string {
  const configured: unknown = Constants.expoConfig?.extra?.apiUrl
  return typeof configured === 'string' ? configured : 'http://10.0.2.2:5173'
}

export function getNormalizedServerUrl(rawUrl: string): string | null {
  const trimmed = rawUrl.trim().replace(/\/+$/, '')
  return /^https?:\/\/[^\s/]+(\/\S*)?$/i.test(trimmed) ? trimmed : null
}

export async function getServerUrl(): Promise<string> {
  try {
    return (await AsyncStorage.getItem(SERVER_URL_KEY)) ?? getDefaultServerUrl()
  } catch {
    return getDefaultServerUrl()
  }
}

export async function setServerUrl(serverUrl: string | null): Promise<void> {
  if (serverUrl === null) await AsyncStorage.removeItem(SERVER_URL_KEY)
  else await AsyncStorage.setItem(SERVER_URL_KEY, serverUrl)
}
