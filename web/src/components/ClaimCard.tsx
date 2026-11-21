import { ExternalLink, Scale } from 'lucide-react'

import type { Citation, ClaimResult, ContextNotice, Verdict } from '../api/types'
import { getHostname } from '../lib/format'
import { useMessages } from '../lib/i18n'
import { STRENGTH_STEPS, VERDICT_STYLES } from '../lib/verdicts'
import { Notice } from './Notice'
import { VerdictBadge } from './VerdictBadge'

const CITATION_MARKER = /(\[\d+\])/g
const NO_STRENGTH_VERDICTS = new Set<Verdict>(['nie_podlega_weryfikacji', 'brak_wystarczajacych_dowodow'])

function getCitationAnchor(claimId: string, number: number): string {
  return `zrodlo-${claimId}-${number}`
}

function ExplanationText({ claimId, text }: { claimId: string; text: string }) {
  const { claim } = useMessages()
  return (
    <p className="text-body text-ink">
      {text.split(CITATION_MARKER).map((part, index) => {
        const number = /^\[(\d+)\]$/.exec(part)?.[1]
        if (!number) return part
        return (
          <a
            key={index}
            href={`#${getCitationAnchor(claimId, Number(number))}`}
            className="mx-0.5 inline-flex min-w-5 items-center justify-center rounded-sm border border-border-control px-1 align-text-top font-mono text-meta text-ink hover:border-brand-600 hover:text-brand-700"
            aria-label={claim.sourceLabel(number)}
          >
            {number}
          </a>
        )
      })}
    </p>
  )
}

function StrengthMeter({ strength }: { strength: NonNullable<ClaimResult['strength']> }) {
  const { claim, strengthLevels } = useMessages()
  const steps = STRENGTH_STEPS[strength.level]
  const { factors } = strength
  const facts = [
    { label: claim.independentSources, value: String(factors.independent_sources) },
    { label: claim.bestTier, value: factors.best_tier ?? '–' },
    {
      label: claim.newestAge,
      value: factors.freshness_days === null ? claim.noDate : claim.days(factors.freshness_days),
    },
    { label: claim.quoteAgreement, value: `${Math.round(factors.agreement * 100)}%` },
  ]
  return (
    <div className="rounded-md border border-border p-4">
      <div className="flex items-center gap-3">
        <span className="flex gap-1" aria-hidden>
          {[1, 2, 3].map((step) => (
            <span key={step} className={`h-2 w-6 rounded-pill ${step <= steps ? 'bg-ink' : 'bg-surface-sunken'}`} />
          ))}
        </span>
        <p className="text-body-sm text-ink">
          {claim.strength}: <span className="font-semibold">{strengthLevels[strength.level]}</span>
        </p>
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-4">
        {facts.map((fact) => (
          <div key={fact.label}>
            <dt className="text-meta text-ink-subtle">{fact.label}</dt>
            <dd className="font-mono text-body-sm text-ink">{fact.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

function InterpretationBlock({ claim }: { claim: ClaimResult }) {
  const messages = useMessages().claim
  return (
    <section aria-label={messages.interpretation} className="flex flex-col gap-4">
      <h4 className="flex items-center gap-2 text-label uppercase tracking-wide text-ink-muted">
        <Scale aria-hidden className="size-4" />
        {messages.interpretation}
      </h4>
      <ExplanationText claimId={claim.claim_id} text={claim.explanation_pl} />
      {claim.missing_context_pl && (
        <Notice tone="warning" title={messages.missingContext}>
          {claim.missing_context_pl}
        </Notice>
      )}
      {claim.conflicts.map((conflict) => (
        <Notice key={conflict.summary_pl} tone="warning" title={messages.sourcesDiffer}>
          {conflict.summary_pl}{' '}
          {conflict.citations.map((number) => (
            <a
              key={number}
              href={`#${getCitationAnchor(claim.claim_id, number)}`}
              className="font-mono text-meta underline"
            >
              [{number}]
            </a>
          ))}
        </Notice>
      ))}
      {claim.unresolved_pl && (
        <Notice tone="neutral" title={messages.unresolved}>
          {claim.unresolved_pl}
        </Notice>
      )}
      {claim.strength && !NO_STRENGTH_VERDICTS.has(claim.verdict) && <StrengthMeter strength={claim.strength} />}
    </section>
  )
}

function CitationItem({ claimId, citation }: { claimId: string; citation: Citation }) {
  const { claim, sourceTypes } = useMessages()
  return (
    <li
      id={getCitationAnchor(claimId, citation.n)}
      className="flex scroll-mt-24 gap-3 rounded-md p-2 target:bg-brand-50"
    >
      <span className="mt-1 inline-flex size-6 shrink-0 items-center justify-center rounded-sm border border-border-control bg-surface font-mono text-meta text-ink">
        {citation.n}
      </span>
      <div className="flex min-w-0 flex-col gap-2">
        <blockquote className="font-serif text-quote text-ink italic">„{citation.quote}”</blockquote>
        <a
          href={citation.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex w-fit items-center gap-1 text-body-sm font-medium text-brand-700 underline underline-offset-2"
        >
          {citation.title.replace(/ - Portal Gov\.pl$/, '')}
          <ExternalLink aria-hidden className="size-3.5 shrink-0" />
          <span className="sr-only">{claim.opensInNewTab}</span>
        </a>
        <p className="font-mono text-meta break-words text-ink-subtle">
          {citation.publisher} · {getHostname(citation.url)} · {sourceTypes[citation.source_type]} · {claim.published}{' '}
          {citation.published_at ?? claim.noDate} · {claim.retrieved} {citation.retrieved_at}
        </p>
        {citation.archival && (
          <span className="w-fit rounded-sm bg-warning-bg px-2 py-0.5 text-label text-warning">
            {claim.archival}
          </span>
        )}
      </div>
    </li>
  )
}

function SourcesBlock({ claim }: { claim: ClaimResult }) {
  const messages = useMessages().claim
  return (
    <section aria-label={messages.whatSourcesSay} className="flex flex-col gap-3 rounded-lg bg-surface-subtle p-4 sm:p-5">
      <div>
        <h4 className="text-label uppercase tracking-wide text-ink-muted">{messages.whatSourcesSay}</h4>
        <p className="text-body-sm text-ink-subtle">{messages.verbatimQuotes}</p>
      </div>
      {claim.citations.length > 0 ? (
        <ol className="flex flex-col gap-2">
          {claim.citations.map((citation) => (
            <CitationItem key={citation.n} claimId={claim.claim_id} citation={citation} />
          ))}
        </ol>
      ) : (
        <p className="text-body-sm text-ink-muted">
          {messages.noFragments}
        </p>
      )}
    </section>
  )
}

function ContextNotices({ notices }: { notices: ContextNotice[] }) {
  const { claim } = useMessages()
  if (notices.length === 0) return null
  return (
    <div className="flex flex-col gap-2">
      {notices.map((notice) => (
        <Notice
          key={notice.text_pl}
          tone={notice.kind === 'incident_match' ? 'system' : 'warning'}
          title={claim.noticeTitles[notice.kind]}
        >
          {notice.text_pl}
        </Notice>
      ))}
    </div>
  )
}

export function ClaimCard({ claim, index, total }: { claim: ClaimResult; index: number; total: number }) {
  const messages = useMessages()
  const { borderClass } = VERDICT_STYLES[claim.verdict]
  return (
    <article
      aria-labelledby={`twierdzenie-${claim.claim_id}`}
      className={`overflow-hidden rounded-lg border border-border border-t-4 ${borderClass} bg-surface shadow-card`}
    >
      <header className="flex flex-col gap-3 border-b border-border p-4 sm:p-6">
        <p className="font-mono text-meta text-ink-subtle">
          {messages.claim.position(index + 1, total)}
        </p>
        <h3 id={`twierdzenie-${claim.claim_id}`} className="text-heading font-semibold text-ink">
          {claim.text}
        </h3>
        <div className="flex flex-wrap items-center gap-3">
          <VerdictBadge verdict={claim.verdict} />
          <p className="text-body-sm text-ink-muted">{messages.verdicts[claim.verdict].description}</p>
        </div>
      </header>
      <div className="grid gap-6 p-4 sm:p-6 ">
        <InterpretationBlock claim={claim} />
        <SourcesBlock claim={claim} />
      </div>
      {claim.context_notices.length > 0 && (
        <div className="border-t border-border p-4 sm:px-6">
          <ContextNotices notices={claim.context_notices} />
        </div>
      )}
    </article>
  )
}
