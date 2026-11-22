import type { CheckStatus, StrengthLevel, Verdict } from '@/api/types'

/** DESIGN.md §2.3: every verdict is label + distinct shape + colour. Same copy as web/src/locales/pl.ts. */
export const VERDICT_LABELS: Record<Verdict, { label: string; symbol: string }> = {
  potwierdzone: { label: 'Potwierdzone', symbol: '✓' },
  falszywe: { label: 'Fałszywe', symbol: '✕' },
  wprowadzajace_w_blad: { label: 'Wprowadzające w błąd', symbol: '!' },
  brak_wystarczajacych_dowodow: { label: 'Brak wystarczających dowodów', symbol: '–' },
  nie_podlega_weryfikacji: { label: 'Nie podlega weryfikacji', symbol: '…' },
}

/** Same as the Discord bot and extension: no evidence strength without a decision. */
export const NO_STRENGTH_VERDICTS: ReadonlySet<Verdict> = new Set([
  'brak_wystarczajacych_dowodow',
  'nie_podlega_weryfikacji',
])

export const STATUS_TITLES: Record<Exclude<CheckStatus, 'ok'>, string> = {
  needs_clarification: 'Potrzebujemy doprecyzowania',
  out_of_scope: 'To zgłoszenie jest poza zakresem',
  technical_error: 'Nie udało się wykonać sprawdzenia',
  rate_limited: 'Za dużo zapytań',
}

export const STRENGTH_LABELS: Record<StrengthLevel, string> = { wysoka: 'wysoka', srednia: 'średnia', niska: 'niska' }

export const ERRORS = {
  offline: 'Nie możemy połączyć się z serwerem Prawdowida. Sprawdź połączenie lub adres serwera w ustawieniach.',
  invalid: 'Nie możemy przyjąć tego zgłoszenia. Sprawdź tekst, link lub zrzut ekranu.',
  notFound: 'Nie znaleźliśmy tego sprawdzenia. Mogło zostać usunięte po 30 dniach.',
  unavailable: 'Serwer Prawdowida jest chwilowo niedostępny. Spróbuj ponownie za chwilę.',
  imageTooLarge: 'Ten obraz jest za duży. Wybierz mniejszy zrzut ekranu.',
  imageUnreadable: 'Nie udało się odczytać tego obrazu.',
}

export const TRANSPARENCY_NOTE = 'Wspierane przez AI: zawsze zajrzyj do źródeł. Prawdowid nie jest „sędzią prawdy”.'
