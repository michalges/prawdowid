import { useSyncExternalStore } from 'react'

import { en } from '../locales/en'
import { pl } from '../locales/pl'
import type { Messages } from '../locales/pl'

export type Locale = 'pl' | 'en'

const STORAGE_KEY = 'prawdowid.locale'
const MESSAGES: Record<Locale, Messages> = { pl, en }
const listeners = new Set<() => void>()

function isLocale(value: unknown): value is Locale {
  return value === 'pl' || value === 'en'
}

function getInitialLocale(): Locale {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (isLocale(stored)) return stored
  } catch {
    // Storage can be unavailable (private mode); fall back to the browser language.
  }
  return navigator.language.toLowerCase().startsWith('pl') ? 'pl' : 'en'
}

let currentLocale: Locale = getInitialLocale()
document.documentElement.lang = currentLocale

export function getLocale(): Locale {
  return currentLocale
}

/** For code outside React (API errors); components use `useMessages`. */
export function getMessages(): Messages {
  return MESSAGES[currentLocale]
}

export function setLocale(locale: Locale) {
  currentLocale = locale
  document.documentElement.lang = locale
  try {
    localStorage.setItem(STORAGE_KEY, locale)
  } catch {
    // Not persisted; the choice still applies for this visit.
  }
  listeners.forEach((listener) => listener())
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function useLocale(): Locale {
  return useSyncExternalStore(subscribe, getLocale)
}

export function useMessages(): Messages {
  return MESSAGES[useLocale()]
}
