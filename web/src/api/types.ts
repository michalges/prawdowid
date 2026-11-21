/** Mirrors backend/src/prawdowid/schemas.py (CONCEPT §7.1). */

export type Channel = 'web' | 'discord' | 'demo_chat' | 'mobile'

export type CheckInput =
  | { type: 'text'; text: string }
  | { type: 'url'; url: string; text?: string }
  | { type: 'image'; image_b64: string; text?: string }

export type CheckRequest = {
  channel: Channel
  session_id: string
  input: CheckInput
  language?: 'pl' | 'en'
}

export type CheckStatus = 'ok' | 'needs_clarification' | 'out_of_scope' | 'technical_error' | 'rate_limited'

export type Verdict =
  | 'potwierdzone'
  | 'falszywe'
  | 'wprowadzajace_w_blad'
  | 'brak_wystarczajacych_dowodow'
  | 'nie_podlega_weryfikacji'

export type StrengthLevel = 'wysoka' | 'srednia' | 'niska'
export type QualityTier = 'A' | 'B' | 'C'
export type SourceType = 'official_primary' | 'fact_check' | 'disinfo_db' | 'media_reference'

export type Citation = {
  n: number
  title: string
  publisher: string
  published_at: string | null
  retrieved_at: string
  url: string
  quote: string
  source_type: SourceType
  archival: boolean
}

export type ContextNotice = {
  kind: 'incident_match' | 'source_status' | 'archival_material'
  text_pl: string
}

export type ClaimResult = {
  claim_id: string
  text: string
  verdict: Verdict
  explanation_pl: string
  strength: {
    level: StrengthLevel
    factors: {
      independent_sources: number
      best_tier: QualityTier | null
      freshness_days: number | null
      agreement: number
    }
  } | null
  missing_context_pl: string | null
  conflicts: { summary_pl: string; citations: number[] }[]
  unresolved_pl: string | null
  citations: Citation[]
  context_notices: ContextNotice[]
}

export type CaseInfo = {
  case_id: string
  status: 'zalecamy_przekazanie' | 'przekazano_moderatorowi'
  similar_reports: number
  message_pl: string
}

export type CheckResult = {
  check_id: string
  status: CheckStatus
  status_message_pl: string | null
  claims: ClaimResult[]
  extracted_text_pl: string | null
  input_notices_pl: string[]
  limitations_pl: string[]
  case: CaseInfo | null
  model_info: { llm: string; corpus_version: string | null }
  latency_ms: number
  est_cost_usd: number
}

export type SourceInfo = {
  id: string
  name: string
  publisher: string
  domain: string
  urls: string[]
  type: SourceType
  quality_tier: QualityTier
  fetch_mode: string
  use: 'evidence' | 'context_only' | 'pointer'
  license: string
  license_verified: boolean
  qualification: string
  excluded: boolean
  exclusion_reason: string | null
  documents: number
}

export type SourceCatalog = {
  corpus_version: string | null
  documents: number
  chunks: number
  sources: SourceInfo[]
}

export type Health = {
  status: 'ok'
  version: string
  llm_provider: string
  corpus_version: string | null
  corpus_chunks: number
  embedding_model: string
  ocr: string
  factcheck_enabled: boolean
  moderator_notifications: boolean
  data_processing_pl: string
}
