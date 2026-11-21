import type { CheckStatus, StrengthLevel, Verdict } from '../api/types'

function getPolishClaimCount(count: number): string {
  if (count === 1) return '1 twierdzenie'
  const lastDigit = count % 10
  const lastTwo = count % 100
  const isFew = lastDigit >= 2 && lastDigit <= 4 && (lastTwo < 12 || lastTwo > 14)
  return `${count} ${isFew ? 'twierdzenia' : 'twierdzeń'}`
}

export const pl = {
  dateLocale: 'pl-PL',
  layout: {
    home: 'Prawdowid, strona główna',
    skipToContent: 'Przejdź do treści',
    mainNav: 'Główna nawigacja',
    nav: { check: 'Sprawdź', history: 'Historia', sources: 'Źródła', method: 'Jak to działa', discord: 'Discord' },
    language: 'Język',
    openMenu: 'Otwórz menu',
    closeMenu: 'Zamknij menu',
  },
  notFound: { title: 'Nie ma takiej strony', back: 'Wróć do sprawdzania' },
  loading: { result: 'Wczytujemy wynik…', catalog: 'Wczytujemy katalog…' },
  errors: {
    offline: 'Brak połączenia z serwerem Prawdowida.',
    notFound: 'Nie znaleźliśmy tego wyniku. Mógł zostać usunięty.',
    invalid: 'Nie możemy przyjąć tego zgłoszenia. Sprawdź tekst, link lub plik.',
    unavailable: 'Serwer Prawdowida jest teraz niedostępny.',
    generic: 'Coś poszło nie tak. Spróbuj ponownie.',
  },
  check: {
    title: 'Co chcesz sprawdzić?',
    subtitle: 'Porównamy to z oficjalnymi źródłami i pokażemy dosłowne cytaty.',
    progress: [
      'Wyodrębniamy twierdzenia do sprawdzenia…',
      'Przeszukujemy katalog oficjalnych źródeł…',
      'Porównujemy twierdzenia z dosłownymi cytatami…',
      'Sprawdzamy, czy każdy cytat naprawdę jest w źródle…',
    ],
    progressNote: 'Czas sprawdzenia zależy od dostępności źródeł.',
    examplesLabel: 'Przykłady',
    examples: [
      'Rząd przyjął projekt ustawy o ETIAS',
      'Numer informacji drogowej to 19 111',
      'Od jutra pociągi są bezpłatne dla seniorów',
    ],
    yourRequest: 'Twoje zgłoszenie:',
    sendFailed: 'Nie udało się wysłać zgłoszenia',
    notAVerdict: 'To nie jest ocena prawdziwości.',
    threadLabel: 'Sprawdzenia w tej rozmowie',
  },
  form: {
    placeholder: 'Wklej treść wiadomości, posta albo link do artykułu…',
    help: 'Możesz wkleić kilka zdań naraz: rozdzielimy je na osobne twierdzenia. Ctrl+Enter wysyła.',
    addScreenshot: 'Dodaj zrzut ekranu',
    removeImage: 'Usuń obraz',
    screenshot: 'Zrzut ekranu',
    notAnImage: 'Wybierz plik obrazu (PNG, JPG, WEBP).',
    imageTooLarge: 'Obraz jest za duży. Maksymalnie 5 MB.',
    submit: 'Sprawdź',
    submitting: 'Sprawdzamy…',
  },
  result: {
    statusTitles: {
      needs_clarification: 'Potrzebujemy doprecyzowania',
      out_of_scope: 'To zgłoszenie jest poza zakresem',
      technical_error: 'Nie udało się wykonać sprawdzenia',
      rate_limited: 'Za dużo zapytań',
    } satisfies Record<Exclude<CheckStatus, 'ok'>, string>,
    checked: (count: number) => `Sprawdziliśmy ${getPolishClaimCount(count)}`,
    summaryLabel: 'Podsumowanie wyników',
    ignoredInstructions: 'Zignorowaliśmy polecenia w treści',
    ocrText: 'Tekst odczytany z obrazu (może zawierać błędy)',
    limitations: 'Ograniczenia',
    copied: 'Skopiowano link',
    copyLink: 'Kopiuj link do wyniku',
    corpusVersion: 'wersja zbioru źródeł',
    none: 'brak',
    newCheck: 'Nowe sprawdzenie',
    yourRequest: 'Twoje zgłoszenie',
  },
  claim: {
    position: (index: number, total: number) => `Twierdzenie ${index} z ${total}`,
    sourceLabel: (number: string) => `Źródło ${number}`,
    interpretation: 'Interpretacja Prawdowida',
    missingContext: 'Brakujący kontekst',
    sourcesDiffer: 'Źródła się różnią',
    unresolved: 'Czego nie udało się ustalić',
    strength: 'Siła podstawy',
    independentSources: 'Niezależne źródła',
    bestTier: 'Najlepszy poziom źródła',
    newestAge: 'Wiek najnowszego źródła',
    noDate: 'brak daty',
    days: (days: number) => `${days} dni`,
    quoteAgreement: 'Zgodność cytatów',
    whatSourcesSay: 'Co mówią źródła',
    verbatimQuotes: 'Dosłowne cytaty, bez naszej interpretacji.',
    noFragments: 'W katalogu źródeł nie ma fragmentów, które dotyczą tego twierdzenia.',
    opensInNewTab: '(otwiera się w nowej karcie)',
    published: 'opubl.',
    retrieved: 'pobrano',
    archival: 'Materiał archiwalny',
    noticeTitles: {
      incident_match: 'Kontekst: znany przypadek',
      source_status: 'Status źródła',
      archival_material: 'Materiał archiwalny',
    },
  },
  verdicts: {
    potwierdzone: { label: 'Potwierdzone', description: 'Źródła wprost potwierdzają to twierdzenie.' },
    falszywe: { label: 'Fałszywe', description: 'Źródła wprost przeczą temu twierdzeniu.' },
    wprowadzajace_w_blad: {
      label: 'Wprowadzające w błąd',
      description: 'Prawdziwe elementy prowadzą do złego wniosku albo brakuje ważnego kontekstu.',
    },
    brak_wystarczajacych_dowodow: {
      label: 'Brak wystarczających dowodów',
      description: 'Nasze źródła nie pozwalają tego rozstrzygnąć. Nie zgadujemy.',
    },
    nie_podlega_weryfikacji: {
      label: 'Nie podlega weryfikacji',
      description: 'To opinia, ocena albo przewidywanie, a nie fakt do sprawdzenia.',
    },
  } satisfies Record<Verdict, { label: string; description: string }>,
  strengthLevels: { wysoka: 'wysoka', srednia: 'średnia', niska: 'niska' } satisfies Record<StrengthLevel, string>,
  sourceTypes: {
    official_primary: 'źródło urzędowe',
    fact_check: 'weryfikator faktów',
    disinfo_db: 'baza dezinformacji',
    media_reference: 'media',
  },
  transparency: {
    note: 'Wspierane przez AI: zawsze zajrzyj do źródeł. Prawdowid nie jest „sędzią prawdy”.',
  },
  history: {
    title: 'Historia sprawdzeń',
    intro: 'Lista jest zapisana tylko w tej przeglądarce. Na serwerze trzymamy zamaskowaną treść zgłoszeń przez 30 dni.',
    empty: 'Nie masz jeszcze żadnych sprawdzeń.',
    firstCheck: 'Sprawdź pierwszą informację',
    noVerdict: 'bez oceny',
    yourData: 'Twoje dane',
    yourDataIntro: 'Usuwa wszystkie sprawdzenia tej sesji z serwera i czyści historię w przeglądarce.',
    deleteButton: 'Usuń moje dane',
    deleteConfirm: 'Usunąć historię sprawdzeń z tego urządzenia i z serwera Prawdowida?',
    deleted: 'Usunęliśmy Twoje dane z serwera i z tego urządzenia.',
  },
  sources: {
    title: 'Katalog źródeł',
    intro:
      'Jawna lista miejsc, w których szukamy. Poziom A to źródła urzędowe, B to akredytowani weryfikatorzy faktów, C to inne wiarygodne źródła. Samo źródło nigdy nie przesądza o ocenie.',
    stats: (documents: number, chunks: number) => `${documents} dokumentów · ${chunks} fragmentów`,
    documentsShort: (documents: number) => `${documents} dok.`,
    tier: (tier: string) => `poziom ${tier}`,
    licenseUnverified: 'licencja w weryfikacji',
    excluded: 'wykluczone:',
    groups: {
      evidence: {
        title: 'Źródła dowodów',
        description: 'Dokumenty, z których cytujemy. Tylko one mogą potwierdzić lub obalić twierdzenie.',
      },
      pointer: {
        title: 'Dane na żywo',
        description: 'Mapy i serwisy zmieniające się co chwilę. Nie cytujemy ich, tylko do nich odsyłamy.',
      },
      context_only: {
        title: 'Kontekst',
        description: 'Bazy znanych przypadków dezinformacji. Pokazujemy je jako kontekst, nigdy jako podstawę oceny.',
      },
    },
  },
  method: {
    title: 'Jak to działa',
    intro:
      'Prawdowid pomaga ocenić informację na podstawie źródeł. Zawsze oddziela to, co mówią źródła, od naszej interpretacji. Nie jest automatycznym „sędzią prawdy”.',
    stepsTitle: 'Pięć kroków sprawdzenia',
    steps: [
      ['Rozdzielamy treść na twierdzenia', 'Opinie i przewidywania oznaczamy osobno: nie da się ich sprawdzić w źródłach.'],
      ['Szukamy w katalogu źródeł', 'Przeszukujemy jawny katalog stron urzędowych. Nie korzystamy z całego internetu.'],
      ['Porównujemy z cytatami', 'Model językowy porównuje twierdzenie wyłącznie ze znalezionymi fragmentami.'],
      ['Program sprawdza cytaty', 'Każdy cytat musi dosłownie występować w źródle. Jeśli nie występuje, odrzucamy go.'],
      [
        'Stałe reguły decydują o ocenie',
        'Bez potwierdzonego cytatu, przy sprzecznych źródłach lub słabych źródłach piszemy „brak wystarczających dowodów”.',
      ],
    ] as [string, string][],
    verdictsTitle: 'Możliwe wyniki',
    strengthTitle: 'Siła podstawy',
    strengthText:
      'Siłę oceny liczymy z jawnych danych: liczby niezależnych wydawców, poziomu źródeł, ich aktualności i zgodności cytatów z twierdzeniem. Nie pytamy modelu, „jak bardzo jest pewny”.',
    notDoTitle: 'Czego nie robimy',
    notDo: [
      'Nie oceniamy treści po samej domenie, autorze ani popularności.',
      'Nie omijamy płatnych ani zablokowanych stron.',
      'Nie zapisujemy obrazów: zostaje tylko odczytany, zamaskowany tekst.',
    ],
    seeCatalog: 'Zobacz katalog źródeł',
  },
  discord: {
    title: 'Prawdowid na Discordzie',
    intro: 'Sprawdzaj informacje bez wychodzenia z rozmowy. Bot korzysta z tych samych źródeł i reguł co strona.',
    addTitle: 'Dodaj aplikację',
    userInstallTitle: 'Dodaj do swojego konta',
    userInstallText: 'Używaj komendy /sprawdz w wiadomościach prywatnych i na każdym serwerze, bez zgody administratora.',
    guildInstallTitle: 'Dodaj do serwera',
    guildInstallText: 'Bot dostępny dla wszystkich członków serwera. Wymaga uprawnienia „Zarządzanie serwerem”.',
    commandsTitle: 'Komendy',
    commands: [
      ['/sprawdz', 'Sprawdza informację w oficjalnych źródłach i podaje link do pełnego wyniku na stronie.'],
      ['/usun_moje_dane', 'Usuwa z serwera Prawdowida wszystkie Twoje sprawdzenia z Discorda.'],
    ] as [string, string][],
  },
}

export type Messages = typeof pl
