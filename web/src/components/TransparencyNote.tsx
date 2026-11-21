import { getHealth } from '../api/client'
import { useMessages } from '../lib/i18n'
import { useApi } from '../lib/useApi'

/** The always-visible "AI-assisted, check the sources" line (CONCEPT §8), plus model and source collection version. */
export function TransparencyNote({ isDetailed = false }: { isDetailed?: boolean }) {
  const { transparency, result } = useMessages()
  const health = useApi('health', getHealth)
  const model = health.status === 'ready' ? health.data : null
  return (
    <div className="flex flex-col gap-1 text-center text-meta text-ink-subtle">
      <p>{transparency.note}</p>
      {model && isDetailed && <p className="text-body-sm text-ink-muted">{model.data_processing_pl}</p>}
      {model && isDetailed && (
        <p className="font-mono">
          {model.llm_provider} · {result.corpusVersion} {model.corpus_version ?? result.none}
        </p>
      )}
    </div>
  )
}
