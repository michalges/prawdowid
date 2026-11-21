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

export function getShortDateTime(iso: string, dateLocale: string): string {
  return new Date(iso).toLocaleString(dateLocale, { dateStyle: 'medium', timeStyle: 'short' })
}
