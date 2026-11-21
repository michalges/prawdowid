import { useEffect, useRef, useState } from 'react'

import { postCheck } from '../api/client'
import type { CheckInput, CheckResult } from '../api/types'
import { CheckForm } from '../components/CheckForm'
import { ResultView } from '../components/ResultView'
import { TransparencyNote } from '../components/TransparencyNote'
import { setCachedResult } from '../lib/resultCache'
import { getLocale, useMessages } from '../lib/i18n'
import { addHistoryEntry, getSessionId } from '../lib/session'
import { getErrorText } from '../lib/useApi'

const PROGRESS_STEP_COUNT = 4
const STEP_INTERVAL_MS = 4000

type Exchange =
  | { id: number; label: string; state: 'pending'; stepIndex: number }
  | { id: number; label: string; state: 'done'; result: CheckResult }
  | { id: number; label: string; state: 'error'; message: string }

/** Kept outside the component so the conversation survives switching tabs in the app. */
let savedExchanges: Exchange[] = []

function ProgressPanel({ stepIndex }: { stepIndex: number }) {
  const { check } = useMessages()
  return (
    <output className="flex flex-col gap-3 rounded-lg bg-surface-subtle p-5">
      <div className="h-1 overflow-hidden rounded-pill bg-surface-sunken">
        <div
          className="h-full rounded-pill bg-ink transition-all duration-700"
          style={{ width: `${((stepIndex + 1) / PROGRESS_STEP_COUNT) * 100}%` }}
        />
      </div>
      <p className="text-body text-ink">{check.progress[stepIndex]}</p>
      <p className="text-body-sm text-ink-subtle">{check.progressNote}</p>
    </output>
  )
}

function ExampleChips({ onExample }: { onExample: (text: string) => void }) {
  const { check } = useMessages()
  return (
    <ul className="flex flex-wrap justify-center gap-2" aria-label={check.examplesLabel}>
      {check.examples.map((example) => (
        <li key={example}>
          <button
            type="button"
            onClick={() => onExample(example)}
            className="min-h-11 rounded-pill border border-border px-4 text-body-sm text-ink-muted hover:border-border-control hover:text-ink"
          >
            {example}
          </button>
        </li>
      ))}
    </ul>
  )
}

function ExchangeView({ exchange }: { exchange: Exchange }) {
  const { check } = useMessages()
  return (
    <li className="flex flex-col gap-4">
      <div className="ml-auto max-w-[85%] rounded-lg rounded-br-sm bg-surface-subtle px-4 py-3">
        <p className="sr-only">{check.yourRequest}</p>
        <p className="text-body whitespace-pre-wrap text-ink">{exchange.label}</p>
      </div>
      {exchange.state === 'pending' && <ProgressPanel stepIndex={exchange.stepIndex} />}
      {exchange.state === 'done' && <ResultView result={exchange.result} />}
      {exchange.state === 'error' && (
        <div role="alert" className="rounded-lg bg-system-bg p-4 text-body-sm text-ink">
          <p className="font-semibold text-system">{check.sendFailed}</p>
          <p>
            {exchange.message} {check.notAVerdict}
          </p>
        </div>
      )}
    </li>
  )
}

export function CheckPage() {
  const { check } = useMessages()
  const [exchanges, setExchanges] = useState<Exchange[]>(savedExchanges)
  const [draft, setDraft] = useState('')
  const threadEnd = useRef<HTMLDivElement>(null)
  const isBusy = exchanges.some((exchange) => exchange.state === 'pending')

  const isEmpty = exchanges.length === 0

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
            ? { ...exchange, stepIndex: Math.min(exchange.stepIndex + 1, PROGRESS_STEP_COUNT - 1) }
            : exchange,
        ),
      STEP_INTERVAL_MS,
    )
    try {
      const result = await postCheck({ channel: 'web', session_id: getSessionId(), input, language: getLocale() })
      addHistoryEntry(result, label)
      setCachedResult(result, label)
      updateExchange(id, () => ({ id, label, state: 'done', result }))
    } catch (error) {
      updateExchange(id, () => ({ id, label, state: 'error', message: getErrorText(error) }))
    } finally {
      clearInterval(timer)
    }
  }

  const composer = <CheckForm isBusy={isBusy} draft={draft} onDraftChange={setDraft} onSubmit={runCheck} />

  if (isEmpty) {
    return (
      <div className="flex flex-1 flex-col items-center gap-6 pb-12">
        <div className="flex w-full flex-col items-center gap-6 pt-[12vh]">
          <div className="flex flex-col gap-2 text-center">
            <h1 className="text-title font-semibold text-ink">{check.title}</h1>
            <p className="text-body text-ink-muted">{check.subtitle}</p>
          </div>
          <div className="w-full">{composer}</div>
        </div>
        <ExampleChips onExample={setDraft} />
        <TransparencyNote />
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col">
      <ol className="flex flex-col gap-10 py-8" aria-label={check.threadLabel}>
        {exchanges.map((exchange) => (
          <ExchangeView key={exchange.id} exchange={exchange} />
        ))}
      </ol>
      <div ref={threadEnd} />
      <div className="sticky bottom-0 z-1 -mx-4 mt-auto px-4 pt-6 pb-4">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 -top-24 bottom-0 -z-10 mask-[linear-gradient(to_bottom,transparent,rgba(0,0,0,0.12)_1.5rem,rgba(0,0,0,0.55)_4.5rem,black_7rem)] bg-surface/85 backdrop-blur-2xl"
        />
        {composer}
        <div className="mt-3">
          <TransparencyNote />
        </div>
      </div>
    </div>
  )
}
