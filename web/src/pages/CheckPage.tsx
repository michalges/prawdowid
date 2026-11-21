import { BookOpenCheck, CircleDashed, Quote } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { postCheck } from '../api/client'
import type { CheckInput, CheckResult } from '../api/types'
import { CheckForm } from '../components/CheckForm'
import { ResultView } from '../components/ResultView'
import { TransparencyNote } from '../components/TransparencyNote'
import { setCachedResult } from '../lib/resultCache'
import { addHistoryEntry, getSessionId } from '../lib/session'
import { getErrorText } from '../lib/useApi'

const PROGRESS_STEPS = [
  'Wyodrębniamy twierdzenia do sprawdzenia…',
  'Przeszukujemy katalog oficjalnych źródeł…',
  'Porównujemy twierdzenia z dosłownymi cytatami…',
  'Sprawdzamy, czy każdy cytat naprawdę jest w źródle…',
]
const STEP_INTERVAL_MS = 4000

const PRINCIPLES = [
  { Icon: BookOpenCheck, title: 'Tylko jawne źródła', text: 'Każdy wynik prowadzi do konkretnego dokumentu.' },
  { Icon: Quote, title: 'Cytaty sprawdza program', text: 'Pokazujemy tylko fragmenty, które naprawdę są w źródle.' },
  { Icon: CircleDashed, title: 'Mówimy, gdy nie wiemy', text: 'Gdy źródeł brakuje, nie zgadujemy.' },
]

const EXAMPLES = [
  'Rada Ministrów przyjęła w listopadzie 2026 projekt ustawy o systemie ETIAS.',
  'Numer Informacji Drogowej GDDKiA to 19 111.',
  'Od jutra wszystkie pociągi w Polsce będą bezpłatne dla seniorów.',
]

type Exchange =
  | { id: number; label: string; state: 'pending'; stepIndex: number }
  | { id: number; label: string; state: 'done'; result: CheckResult }
  | { id: number; label: string; state: 'error'; message: string }

/** Kept outside the component so the conversation survives switching tabs in the app. */
let savedExchanges: Exchange[] = []

function ProgressPanel({ stepIndex }: { stepIndex: number }) {
  return (
    <output className="flex flex-col gap-3 rounded-lg bg-surface-subtle p-5">
      <div className="h-1 overflow-hidden rounded-pill bg-surface-sunken">
        <div
          className="h-full rounded-pill bg-ink transition-all duration-700"
          style={{ width: `${((stepIndex + 1) / PROGRESS_STEPS.length) * 100}%` }}
        />
      </div>
      <p className="text-body text-ink">{PROGRESS_STEPS[stepIndex]}</p>
      <p className="text-body-sm text-ink-subtle">Zwykle trwa to od 10 do 30 sekund.</p>
    </output>
  )
}

function EmptyState({ onExample }: { onExample: (text: string) => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-8 py-10 text-center">
      <div className="flex max-w-xl flex-col gap-3">
        <h1 className="text-title font-semibold text-ink sm:text-display">Sprawdź, zanim przekażesz dalej</h1>
        <p className="text-body text-ink-muted">
          Wklej wiadomość, link albo zrzut ekranu. Porównamy każde twierdzenie z oficjalnymi źródłami i pokażemy
          dosłowne cytaty. Ocenę zostawiamy Tobie.
        </p>
      </div>
      <ul className="grid w-full gap-3 text-left sm:grid-cols-3">
        {PRINCIPLES.map(({ Icon, title, text }) => (
          <li key={title} className="flex flex-col gap-1 rounded-lg border border-border p-4">
            <Icon aria-hidden className="size-5 text-ink" />
            <span className="text-body-sm font-semibold text-ink">{title}</span>
            <span className="text-body-sm text-ink-muted">{text}</span>
          </li>
        ))}
      </ul>
      <div className="flex w-full flex-col gap-2">
        <p className="text-label tracking-wide text-ink-muted uppercase">Przykłady</p>
        <ul className="flex flex-col gap-2">
          {EXAMPLES.map((example) => (
            <li key={example}>
              <button
                type="button"
                onClick={() => onExample(example)}
                className="min-h-11 w-full rounded-lg border border-border px-4 py-3 text-left text-body-sm text-ink hover:border-border-control hover:bg-surface-subtle"
              >
                {example}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

function ExchangeView({ exchange }: { exchange: Exchange }) {
  return (
    <li className="flex flex-col gap-4">
      <div className="ml-auto max-w-[85%] rounded-lg rounded-br-sm bg-surface-subtle px-4 py-3">
        <p className="sr-only">Twoje zgłoszenie:</p>
        <p className="text-body whitespace-pre-wrap text-ink">{exchange.label}</p>
      </div>
      {exchange.state === 'pending' && <ProgressPanel stepIndex={exchange.stepIndex} />}
      {exchange.state === 'done' && <ResultView result={exchange.result} />}
      {exchange.state === 'error' && (
        <div role="alert" className="rounded-lg bg-system-bg p-4 text-body-sm text-ink">
          <p className="font-semibold text-system">Nie udało się wysłać zgłoszenia</p>
          <p>{exchange.message} To nie jest ocena prawdziwości.</p>
        </div>
      )}
    </li>
  )
}

export function CheckPage() {
  const [exchanges, setExchanges] = useState<Exchange[]>(savedExchanges)
  const [draft, setDraft] = useState('')
  const threadEnd = useRef<HTMLDivElement>(null)
  const isBusy = exchanges.some((exchange) => exchange.state === 'pending')

  useEffect(() => {
    savedExchanges = exchanges
  }, [exchanges])

  function updateExchange(id: number, getNext: (current: Exchange) => Exchange) {
    setExchanges((current) => current.map((exchange) => (exchange.id === id ? getNext(exchange) : exchange)))
  }

  async function runCheck(input: CheckInput, label: string) {
    const id = Date.now()
    setExchanges((current) => [...current, { id, label, state: 'pending', stepIndex: 0 }])
    requestAnimationFrame(() => threadEnd.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }))
    const timer = setInterval(
      () =>
        updateExchange(id, (exchange) =>
          exchange.state === 'pending'
            ? { ...exchange, stepIndex: Math.min(exchange.stepIndex + 1, PROGRESS_STEPS.length - 1) }
            : exchange,
        ),
      STEP_INTERVAL_MS,
    )
    try {
      const result = await postCheck({ channel: 'web', session_id: getSessionId(), input })
      addHistoryEntry(result, label)
      setCachedResult(result, label)
      updateExchange(id, () => ({ id, label, state: 'done', result }))
    } catch (error) {
      updateExchange(id, () => ({ id, label, state: 'error', message: getErrorText(error) }))
    } finally {
      clearInterval(timer)
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      {exchanges.length === 0 ? (
        <EmptyState onExample={setDraft} />
      ) : (
        <ol className="flex flex-col gap-10 py-8" aria-label="Sprawdzenia w tej rozmowie">
          {exchanges.map((exchange) => (
            <ExchangeView key={exchange.id} exchange={exchange} />
          ))}
        </ol>
      )}
      <div ref={threadEnd} />
      <div className="sticky bottom-0 -mx-4 mt-auto bg-linear-to-t from-surface from-70% to-transparent px-4 pt-6 pb-4">
        <CheckForm isBusy={isBusy} draft={draft} onDraftChange={setDraft} onSubmit={runCheck} />
        <div className="mt-3">
          <TransparencyNote />
        </div>
      </div>
    </div>
  )
}
