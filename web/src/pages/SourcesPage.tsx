import { ExternalLink } from 'lucide-react'

import type { SourceCatalog, SourceInfo } from '../api/types'
import { SOURCE_TYPE_LABELS } from '../lib/verdicts'

const GROUPS: { use: SourceInfo['use']; title: string; description: string }[] = [
  {
    use: 'evidence',
    title: 'Źródła dowodów',
    description: 'Dokumenty, z których cytujemy. Tylko one mogą potwierdzić lub obalić twierdzenie.',
  },
  {
    use: 'pointer',
    title: 'Dane na żywo',
    description: 'Mapy i serwisy zmieniające się co chwilę. Nie cytujemy ich, tylko do nich odsyłamy.',
  },
  {
    use: 'context_only',
    title: 'Kontekst',
    description: 'Bazy znanych przypadków dezinformacji. Pokazujemy je jako kontekst, nigdy jako podstawę oceny.',
  },
]

function SourceRow({ source }: { source: SourceInfo }) {
  return (
    <li className="flex flex-col gap-2 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <a
          href={source.urls[0]}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-body font-semibold text-ink hover:text-brand-700"
        >
          {source.name}
          <ExternalLink aria-hidden className="size-3.5" />
        </a>
        <span className="font-mono text-meta text-ink-subtle">
          {source.use === 'evidence' ? `${source.documents} dok.` : source.fetch_mode}
        </span>
      </div>
      <p className="text-body-sm text-ink-muted">
        {source.publisher} · {source.qualification}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-sm border border-border-control px-2 py-0.5 font-mono text-meta text-ink">
          poziom {source.quality_tier}
        </span>
        <span className="rounded-sm bg-surface-subtle px-2 py-0.5 text-label text-ink-muted">
          {SOURCE_TYPE_LABELS[source.type]}
        </span>
        <span className="font-mono text-meta text-ink-subtle">{source.domain}</span>
        {!source.license_verified && (
          <span className="rounded-sm bg-warning-bg px-2 py-0.5 text-label text-warning">licencja w weryfikacji</span>
        )}
        {source.excluded && (
          <span className="rounded-sm bg-surface-sunken px-2 py-0.5 text-label text-ink-muted">
            wykluczone: {source.exclusion_reason}
          </span>
        )}
      </div>
    </li>
  )
}

export function SourcesPage({ catalog }: { catalog: SourceCatalog }) {
  return (
    <div className="flex flex-col gap-8">
      <div className="flex max-w-3xl flex-col gap-2">
        <h1 className="text-title font-semibold text-ink">Katalog źródeł</h1>
        <p className="text-body text-ink-muted">
          Jawna lista miejsc, w których szukamy. Poziom A to źródła urzędowe, B to akredytowani weryfikatorzy faktów, C
          to inne wiarygodne źródła. Samo źródło nigdy nie przesądza o ocenie.
        </p>
        <p className="font-mono text-meta text-ink-subtle">
          {catalog.documents} dokumentów · {catalog.chunks} fragmentów · wersja korpusu{' '}
          {catalog.corpus_version ?? 'brak'}
        </p>
      </div>
      {GROUPS.map((group) => {
        const sources = catalog.sources.filter((source) => source.use === group.use)
        if (sources.length === 0) return null
        return (
          <section key={group.use} className="flex flex-col gap-3">
            <div>
              <h2 className="text-heading font-semibold text-ink">{group.title}</h2>
              <p className="text-body-sm text-ink-muted">{group.description}</p>
            </div>
            <ul className="divide-y divide-border rounded-lg border border-border">
              {sources.map((source) => (
                <SourceRow key={source.id} source={source} />
              ))}
            </ul>
          </section>
        )
      })}
    </div>
  )
}
