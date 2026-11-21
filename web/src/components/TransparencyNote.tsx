import { getHealth } from '../api/client'
import { useApi } from '../lib/useApi'

/** The always-visible "AI-assisted, check the sources" line (CONCEPT §8), plus model and corpus. */
export function TransparencyNote({ isDetailed = false }: { isDetailed?: boolean }) {
  const health = useApi('health', getHealth)
  const model = health.status === 'ready' ? health.data : null
  return (
    <div className="flex flex-col gap-1 text-center text-meta text-ink-subtle">
      <p>Wspierane przez AI: zawsze zajrzyj do źródeł. Prawdowid nie jest „sędzią prawdy”.</p>
      {model && isDetailed && <p className="text-body-sm text-ink-muted">{model.data_processing_pl}</p>}
      {model && isDetailed && (
        <p className="font-mono">
          {model.llm_provider} · korpus {model.corpus_version ?? 'brak'}
        </p>
      )}
    </div>
  )
}
