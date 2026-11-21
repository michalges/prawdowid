import { Link } from '@tanstack/react-router'

import type { Verdict } from '../api/types'
import { VerdictBadge } from '../components/VerdictBadge'
import { VERDICT_STYLES } from '../lib/verdicts'

const STEPS = [
  ['Rozdzielamy treść na twierdzenia', 'Opinie i przewidywania oznaczamy osobno: nie da się ich sprawdzić w źródłach.'],
  ['Szukamy w katalogu źródeł', 'Przeszukujemy jawny katalog stron urzędowych. Nie korzystamy z całego internetu.'],
  ['Porównujemy z cytatami', 'Model językowy porównuje twierdzenie wyłącznie ze znalezionymi fragmentami.'],
  ['Program sprawdza cytaty', 'Każdy cytat musi dosłownie występować w źródle. Jeśli nie występuje, odrzucamy go.'],
  [
    'Stałe reguły decydują o ocenie',
    'Bez potwierdzonego cytatu, przy sprzecznych źródłach lub słabych źródłach piszemy „brak wystarczających dowodów”.',
  ],
] as const

export function MethodPage() {
  return (
    <div className="flex max-w-3xl flex-col gap-10">
      <section className="flex flex-col gap-3">
        <h1 className="text-title font-semibold text-ink">Jak to działa</h1>
        <p className="text-body text-ink-muted">
          Prawdowid pomaga ocenić informację na podstawie źródeł. Zawsze oddziela to, co mówią źródła, od naszej
          interpretacji. Nie jest automatycznym „sędzią prawdy”.
        </p>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-heading font-semibold text-ink">Pięć kroków sprawdzenia</h2>
        <ol className="flex flex-col gap-4">
          {STEPS.map(([title, text], index) => (
            <li key={title} className="flex gap-4">
              <span className="flex size-8 shrink-0 items-center justify-center rounded-pill bg-surface-subtle font-mono text-body-sm text-ink">
                {index + 1}
              </span>
              <div>
                <h3 className="text-body font-semibold text-ink">{title}</h3>
                <p className="text-body-sm text-ink-muted">{text}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-heading font-semibold text-ink">Możliwe wyniki</h2>
        <ul className="flex flex-col gap-3">
          {(Object.keys(VERDICT_STYLES) as Verdict[]).map((verdict) => (
            <li key={verdict} className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
              <span className="sm:w-72">
                <VerdictBadge verdict={verdict} />
              </span>
              <span className="text-body-sm text-ink-muted">{VERDICT_STYLES[verdict].description}</span>
            </li>
          ))}
        </ul>
        <p className="text-body-sm text-ink-muted">
          Awaria, zbyt wiele zapytań albo niejasne pytanie to nie są oceny. Pokazujemy je osobno, na niebiesko.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-heading font-semibold text-ink">Siła podstawy</h2>
        <p className="text-body text-ink-muted">
          Siłę oceny liczymy z jawnych danych: liczby niezależnych wydawców, poziomu źródeł, ich aktualności i zgodności
          cytatów z twierdzeniem. Nie pytamy modelu, „jak bardzo jest pewny”.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-heading font-semibold text-ink">Czego nie robimy</h2>
        <ul className="flex list-disc flex-col gap-1 pl-5 text-body text-ink-muted">
          <li>Nie oceniamy treści po samej domenie, autorze ani popularności.</li>
          <li>Nie twierdzimy, że wykrywamy obrazy wygenerowane przez AI.</li>
          <li>Nie omijamy płatnych ani zablokowanych stron.</li>
          <li>Nie zapisujemy obrazów: zostaje tylko odczytany, zamaskowany tekst.</li>
        </ul>
        <Link to="/zrodla" className="w-fit font-medium text-brand-700 underline underline-offset-2">
          Zobacz katalog źródeł
        </Link>
      </section>
    </div>
  )
}
