import { Link } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'

import { ResultView } from '../components/ResultView'
import type { CachedResult } from '../lib/resultCache'

export function ResultPage({ cached }: { cached: CachedResult }) {
  return (
    <div className="flex flex-col gap-6">
      <Link
        to="/"
        className="inline-flex min-h-11 w-fit items-center gap-2 rounded-md text-body-sm font-medium text-brand-700"
      >
        <ArrowLeft aria-hidden className="size-4" />
        Nowe sprawdzenie
      </Link>

      {cached.label && (
        <section className="rounded-lg bg-surface-subtle p-4">
          <h1 className="text-label uppercase tracking-wide text-ink-muted">Twoje zgłoszenie</h1>
          <p className="mt-1 line-clamp-4 text-body text-ink">{cached.label}</p>
        </section>
      )}

      <ResultView result={cached.result} />
    </div>
  )
}
