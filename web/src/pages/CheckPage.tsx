import { BookOpenCheck, CircleDashed, Quote } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from '@tanstack/react-router'

import { postCheck } from '../api/client'
import type { CheckInput } from '../api/types'
import { CheckForm } from '../components/CheckForm'
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
  {
    Icon: BookOpenCheck,
    title: 'Tylko jawne źródła',
    text: 'Szukamy w opisanym katalogu stron urzędowych. Każdy wynik prowadzi do konkretnego dokumentu.',
  },
  {
    Icon: Quote,
    title: 'Cytaty sprawdzane przez program',
    text: 'Pokazujemy tylko fragmenty, które naprawdę są w źródle. Model językowy nie może ich wymyślić.',
  },
  {
    Icon: CircleDashed,
    title: 'Mówimy, gdy nie wiemy',
    text: 'Jeśli źródła nie wystarczają, nie zgadujemy. Napiszemy, czego nie udało się ustalić.',
  },
]

function ProgressPanel({ stepIndex }: { stepIndex: number }) {
  return (
    <output className="flex flex-col gap-4 rounded-lg bg-surface-subtle p-6">
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

export function CheckPage() {
  const navigate = useNavigate()
  const [stepIndex, setStepIndex] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function runCheck(input: CheckInput, label: string) {
    setError(null)
    setStepIndex(0)
    const timer = setInterval(
      () => setStepIndex((step) => Math.min((step ?? 0) + 1, PROGRESS_STEPS.length - 1)),
      STEP_INTERVAL_MS,
    )
    try {
      const result = await postCheck({ channel: 'web', session_id: getSessionId(), input })
      addHistoryEntry(result, label)
      setCachedResult(result, label)
      await navigate({ to: '/wynik/$checkId', params: { checkId: result.check_id } })
    } catch (requestError) {
      setError(getErrorText(requestError))
      setStepIndex(null)
    } finally {
      clearInterval(timer)
    }
  }

  return (
    <div className="flex flex-col gap-10">
      <section className="flex max-w-3xl flex-col gap-3">
        <h1 className="text-title font-semibold text-ink sm:text-display">Sprawdź, zanim przekażesz dalej</h1>
        <p className="text-body text-ink-muted">
          Wklej wiadomość, link albo zrzut ekranu. Porównamy każde twierdzenie z oficjalnymi źródłami i pokażemy
          dosłowne cytaty. Ocenę zostawiamy Tobie.
        </p>
      </section>

      <section className="max-w-3xl">
        <CheckForm isBusy={stepIndex !== null} onSubmit={runCheck} />
        {error && (
          <div role="alert" className="mt-4 rounded-lg bg-system-bg p-4 text-body-sm text-ink">
            <p className="font-semibold text-system">Nie udało się wysłać zgłoszenia</p>
            <p>{error} To nie jest ocena prawdziwości.</p>
          </div>
        )}
        {stepIndex !== null && (
          <div className="mt-6">
            <ProgressPanel stepIndex={stepIndex} />
          </div>
        )}
      </section>

      <section aria-label="Jak pracujemy" className="grid gap-4 sm:grid-cols-3">
        {PRINCIPLES.map(({ Icon, title, text }) => (
          <div key={title} className="flex flex-col gap-2 rounded-lg border border-border p-5">
            <Icon aria-hidden className="size-5 text-ink" />
            <h2 className="text-body font-semibold text-ink">{title}</h2>
            <p className="text-body-sm text-ink-muted">{text}</p>
          </div>
        ))}
      </section>
    </div>
  )
}
