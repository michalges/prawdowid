const MONTHS = [
  'stycznia',
  'lutego',
  'marca',
  'kwietnia',
  'maja',
  'czerwca',
  'lipca',
  'sierpnia',
  'września',
  'października',
  'listopada',
  'grudnia',
]

/** "2026-10-02" → "2 października 2026 r." (DESIGN.md §7: words in sentences, ISO in metadata). */
export function getDateInWords(isoDate: string): string {
  const [year, month, day] = isoDate.slice(0, 10).split('-').map(Number)
  if (!year || !month || !day) return isoDate
  return `${day} ${MONTHS[month - 1]} ${year} r.`
}

export function getHostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

export function getClaimCountLabel(count: number): string {
  if (count === 1) return '1 twierdzenie'
  const lastDigit = count % 10
  const lastTwo = count % 100
  const isFew = lastDigit >= 2 && lastDigit <= 4 && (lastTwo < 12 || lastTwo > 14)
  return `${count} ${isFew ? 'twierdzenia' : 'twierdzeń'}`
}

export function getShortDateTime(iso: string): string {
  return new Date(iso).toLocaleString('pl-PL', { dateStyle: 'medium', timeStyle: 'short' })
}
