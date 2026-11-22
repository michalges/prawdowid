import type { CheckInput } from '@/api/types'

const MAX_TEXT_CHARS = 10_000
const URL_ONLY = /^\s*(https?:\/\/\S+)\s*$/i
const TRAILING_URL = /(https?:\/\/\S+)\s*$/i

/** Same rule as the Discord bot and extension: text that is only a link is checked as a link. */
export function getTextOrUrlInput(rawText: string): CheckInput | null {
  const text = rawText.trim().slice(0, MAX_TEXT_CHARS)
  if (!text) return null
  const urlMatch = URL_ONLY.exec(text)
  return urlMatch?.[1] ? { type: 'url', url: urlMatch[1] } : { type: 'text', text }
}

/**
 * Browsers share "page title\nhttps://…" or put the title in EXTRA_SUBJECT. Keep just the link
 * when the rest is only the title, so the check reads the page instead of the title.
 */
export function getSharedText(text: string, subject: string | null): string {
  const urlMatch = TRAILING_URL.exec(text)
  if (!urlMatch?.[1]) return text
  const rest = text.slice(0, urlMatch.index).trim()
  return !rest || rest === subject?.trim() ? urlMatch[1] : text
}

export function getLabel(input: CheckInput): string {
  if (input.type === 'url') return input.url
  if (input.type === 'image') return 'Zrzut ekranu'
  return input.text.length > 140 ? `${input.text.slice(0, 139)}…` : input.text
}
