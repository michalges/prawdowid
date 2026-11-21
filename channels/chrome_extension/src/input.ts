import type { CheckInput } from './types.js'

const MAX_TEXT_CHARS = 10_000
const URL_ONLY = /^\s*(https?:\/\/\S+)\s*$/i

export function isCheckableUrl(url: string | undefined): url is string {
  return url !== undefined && /^https?:\/\//i.test(url)
}

/** Same rule as the Discord bot: a message that is only a link is checked as a link. */
export function getTextOrUrlInput(rawText: string): CheckInput | null {
  const text = rawText.trim().slice(0, MAX_TEXT_CHARS)
  if (!text) return null
  const urlMatch = URL_ONLY.exec(text)
  return urlMatch?.[1] ? { type: 'url', url: urlMatch[1] } : { type: 'text', text }
}

export function getLabel(input: CheckInput): string {
  if (input.type === 'url') return input.url
  if (input.type === 'image') return 'Zrzut ekranu'
  return input.text.length > 140 ? `${input.text.slice(0, 139)}…` : input.text
}
