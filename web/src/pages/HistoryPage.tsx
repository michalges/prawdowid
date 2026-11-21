import { Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from '@tanstack/react-router'

import { deleteSession } from '../api/client'
import { VerdictBadge } from '../components/VerdictBadge'
import { getShortDateTime } from '../lib/format'
import { clearLocalData, getHistory, getSessionId } from '../lib/session'
import { getErrorText } from '../lib/useApi'

export function HistoryPage() {
  const [entries, setEntries] = useState(getHistory)
  const [message, setMessage] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  async function deleteMyData() {
    if (!window.confirm('Usunąć historię sprawdzeń z tego urządzenia i z serwera Prawdowida?')) return
    setIsDeleting(true)
    try {
      await deleteSession(getSessionId())
      clearLocalData()
      setEntries([])
      setMessage('Usunęliśmy Twoje dane z serwera i z tego urządzenia.')
    } catch (error) {
      setMessage(getErrorText(error))
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div className="flex flex-col py-8 gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-title font-semibold text-ink">Historia sprawdzeń</h1>
        <p className="text-body text-ink-muted">
          Lista jest zapisana tylko w tej przeglądarce. Na serwerze trzymamy zamaskowaną treść zgłoszeń przez 30 dni.
        </p>
      </div>

      {entries.length === 0 ? (
        <p className="rounded-lg bg-surface-subtle p-6 text-body text-ink-muted">
          Nie masz jeszcze żadnych sprawdzeń.{' '}
          <Link to="/" className="font-medium text-brand-700 underline underline-offset-2">
            Sprawdź pierwszą informację
          </Link>
          .
        </p>
      ) : (
        <ul className="flex flex-col divide-y divide-border rounded-lg border border-border">
          {entries.map((entry) => (
            <li key={entry.checkId}>
              <Link
                to="/wynik/$checkId"
                params={{ checkId: entry.checkId }}
                className="flex flex-col gap-2 p-4 hover:bg-surface-subtle"
              >
                <span className="line-clamp-2 text-body text-ink">{entry.label}</span>
                <span className="flex flex-wrap items-center gap-2">
                  {entry.verdicts.map((verdict, index) => (
                    <VerdictBadge key={index} verdict={verdict} size="sm" />
                  ))}
                  {entry.status !== 'ok' && (
                    <span className="rounded-sm bg-system-bg px-2 py-1 text-label text-system">bez oceny</span>
                  )}
                  <span className="font-mono text-meta text-ink-subtle">{getShortDateTime(entry.createdAt)}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <section className="flex flex-col gap-3 rounded-lg border border-border p-5">
        <h2 className="text-heading font-semibold text-ink">Twoje dane</h2>
        <p className="text-body-sm text-ink-muted">
          Usuwa wszystkie sprawdzenia tej sesji z serwera i czyści historię w przeglądarce.
        </p>
        <button
          type="button"
          onClick={deleteMyData}
          disabled={isDeleting}
          className="inline-flex min-h-11 w-fit items-center gap-2 rounded-md border border-border-control px-4 text-body-sm font-semibold text-ink hover:bg-surface-subtle disabled:opacity-60"
        >
          <Trash2 aria-hidden className="size-4" />
          Usuń moje dane
        </button>
        {message && <output className="block text-body-sm text-ink">{message}</output>}
      </section>
    </div>
  )
}
