import { ExternalLink } from 'lucide-react'

import type { SourceCatalog, SourceInfo } from '../api/types'
import { useMessages } from '../lib/i18n'

const GROUP_ORDER: SourceInfo['use'][] = ['evidence', 'pointer', 'context_only']

function SourceRow({ source }: { source: SourceInfo }) {
  const { sources, sourceTypes } = useMessages()
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
          {source.use === 'evidence' ? sources.documentsShort(source.documents) : source.fetch_mode}
        </span>
      </div>
      <p className="text-body-sm text-ink-muted">
        {source.publisher} · {source.qualification}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-sm border border-border-control px-2 py-0.5 font-mono text-meta text-ink">
          {sources.tier(source.quality_tier)}
        </span>
        <span className="rounded-sm bg-surface-subtle px-2 py-0.5 text-label text-ink-muted">
          {sourceTypes[source.type]}
        </span>
        <span className="font-mono text-meta text-ink-subtle">{source.domain}</span>
        {!source.license_verified && (
          <span className="rounded-sm bg-warning-bg px-2 py-0.5 text-label text-warning">{sources.licenseUnverified}</span>
        )}
        {source.excluded && (
          <span className="rounded-sm bg-surface-sunken px-2 py-0.5 text-label text-ink-muted">
            {sources.excluded} {source.exclusion_reason}
          </span>
        )}
      </div>
    </li>
  )
}

export function SourcesPage({ catalog }: { catalog: SourceCatalog }) {
  const { sources: messages, result } = useMessages()
  return (
    <div className="flex flex-col py-8 gap-8">
      <div className="flex max-w-3xl flex-col gap-2">
        <h1 className="text-title font-semibold text-ink">{messages.title}</h1>
        <p className="text-body text-ink-muted">{messages.intro}</p>
        <p className="font-mono text-meta text-ink-subtle">
          {messages.stats(catalog.documents, catalog.chunks)} · {result.corpusVersion}{' '}
          {catalog.corpus_version ?? result.none}
        </p>
      </div>
      {GROUP_ORDER.map((use) => {
        const group = messages.groups[use]
        const sources = catalog.sources.filter((source) => source.use === use)
        if (sources.length === 0) return null
        return (
          <section key={use} className="flex flex-col gap-3">
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
