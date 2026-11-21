import type { CheckStatus, StrengthLevel, Verdict } from './types.js'

/** DESIGN.md §2.3: every verdict is label + distinct shape + colour. Colours live in popup.css. */
export const VERDICT_LABELS: Record<Verdict, { label: string; symbol: string }> = {
  potwierdzone: { label: 'Potwierdzone', symbol: '✓' },
  falszywe: { label: 'Fałszywe', symbol: '✕' },
  wprowadzajace_w_blad: { label: 'Wprowadzające w błąd', symbol: '!' },
  brak_wystarczajacych_dowodow: { label: 'Brak wystarczających dowodów', symbol: '–' },
  nie_podlega_weryfikacji: { label: 'Nie podlega weryfikacji', symbol: '…' },
}

export const STATUS_TITLES: Record<Exclude<CheckStatus, 'ok'>, string> = {
  needs_clarification: 'Potrzebujemy doprecyzowania',
  out_of_scope: 'To zgłoszenie jest poza zakresem',
  technical_error: 'Nie udało się wykonać sprawdzenia',
  rate_limited: 'Za dużo zapytań',
}

/** Same as the Discord bot: no evidence strength without a decision. */
export const NO_STRENGTH_VERDICTS: ReadonlySet<Verdict> = new Set([
  'brak_wystarczajacych_dowodow',
  'nie_podlega_weryfikacji',
])

export const STRENGTH_LABELS: Record<StrengthLevel, string> = { wysoka: 'wysoka', srednia: 'średnia', niska: 'niska' }

export const ERRORS = {
  offline: 'Nie możemy połączyć się z serwerem Prawdowida. Sprawdź adres serwera w ustawieniach.',
  invalid: 'Nie możemy przyjąć tego zgłoszenia. Sprawdź tekst, link lub zrzut ekranu.',
  unavailable: 'Serwer Prawdowida jest chwilowo niedostępny. Spróbuj ponownie za chwilę.',
  timeout: 'Sprawdzenie trwało zbyt długo. Spróbuj ponownie za chwilę.',
  unreadablePage: 'Tej strony nie da się sprawdzić (np. strona wewnętrzna przeglądarki).',
  screenshotFailed: 'Nie udało się zrobić zrzutu ekranu tej karty.',
}

export const MENU_TITLES = {
  selection: 'Sprawdź zaznaczony tekst w Prawdowidzie',
  link: 'Sprawdź ten link w Prawdowidzie',
  page: 'Sprawdź tę stronę w Prawdowidzie',
}
