import { Check, Copy } from 'lucide-react'
import { useState } from 'react'

import type { CheckResult, CheckStatus } from '../api/types'
import { useMessages } from '../lib/i18n'
import { ClaimCard } from './ClaimCard'
import { Notice } from './Notice'
import { VerdictBadge } from './VerdictBadge'

/** DESIGN.md §2.5: technical statuses replace the result and never show verdict colours. */
function StatusPanel({ status, message }: { status: Exclude<CheckStatus, 'ok'>; message: string | null }) {
  const { result } = useMessages()
  return (
    <output className="block rounded-lg bg-system-bg p-6">
      <h2 className="text-heading font-semibold text-system">{result.statusTitles[status]}</h2>
      <p className="mt-2 text-body text-ink">{message}</p>
    </output>
  )
}

function ShareButton({ checkId }: { checkId: string }) {
  const { result } = useMessages()
  const [isCopied, setIsCopied] = useState(false)
  async function copyLink() {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}/wynik/${checkId}`)
      setIsCopied(true)
      setTimeout(() => setIsCopied(false), 2000)
    } catch {
      setIsCopied(false)
    }
  }
  return (
    <button
      type="button"
      onClick={copyLink}
      className="inline-flex min-h-11 items-center gap-2 rounded-md border border-border-control px-4 text-body-sm font-semibold text-ink hover:bg-surface-subtle"
    >
      {isCopied ? <Check aria-hidden className="size-4" /> : <Copy aria-hidden className="size-4" />}
      {isCopied ? result.copied : result.copyLink}
    </button>
  )
}

export function ResultView({ result }: { result: CheckResult }) {
  const messages = useMessages().result
  if (result.status !== 'ok') {
    return <StatusPanel status={result.status} message={result.status_message_pl} />
  }
  return (
    <div className="flex flex-col gap-6">
      <output className="flex flex-col gap-3">
        <h2 className="text-heading font-semibold text-ink">
          {messages.checked(result.claims.length)}
        </h2>
        <ul className="flex flex-wrap gap-2" aria-label={messages.summaryLabel}>
          {result.claims.map((claim) => (
            <li key={claim.claim_id}>
              <a href={`#twierdzenie-${claim.claim_id}`} className="rounded-md">
                <VerdictBadge verdict={claim.verdict} size="sm" />
              </a>
            </li>
          ))}
        </ul>
      </output>

      {result.input_notices_pl.map((notice) => (
        <Notice key={notice} tone="system" title={messages.ignoredInstructions}>
          {notice}
        </Notice>
      ))}

      {result.extracted_text_pl && (
        <details className="rounded-lg border border-border p-4">
          <summary className="cursor-pointer text-body-sm font-semibold text-ink">
            {messages.ocrText}
          </summary>
          <p className="mt-3 whitespace-pre-wrap text-body-sm text-ink-muted">{result.extracted_text_pl}</p>
        </details>
      )}

      {result.claims.map((claim, index) => (
        <ClaimCard key={claim.claim_id} claim={claim} index={index} total={result.claims.length} />
      ))}


      <section className="rounded-lg border border-border p-4 sm:p-5">
        <h2 className="text-label uppercase tracking-wide text-ink-muted">{messages.limitations}</h2>
        <ul className="mt-2 flex list-disc flex-col gap-1 pl-5 text-body-sm text-ink-muted">
          {result.limitations_pl.map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
      </section>

      <div className="flex flex-wrap items-center justify-between gap-4">
        <ShareButton checkId={result.check_id} />
        <p className="font-mono text-meta text-ink-subtle">
          {result.model_info.llm} · {messages.corpusVersion} {result.model_info.corpus_version ?? messages.none} ·{' '}
          {(result.latency_ms / 1000).toFixed(1)} s · id {result.check_id.slice(0, 8)}
        </p>
      </div>
    </div>
  )
}
