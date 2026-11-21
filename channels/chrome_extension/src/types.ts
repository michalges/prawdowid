/** Subset of backend/src/prawdowid/schemas.py (CONCEPT §7.1) that the extension reads. */

export type CheckInput =
  | { type: 'text'; text: string }
  | { type: 'url'; url: string }
  | { type: 'image'; image_b64: string }

export type CheckStatus = 'ok' | 'needs_clarification' | 'out_of_scope' | 'technical_error' | 'rate_limited'

export type Verdict =
  | 'potwierdzone'
  | 'falszywe'
  | 'wprowadzajace_w_blad'
  | 'brak_wystarczajacych_dowodow'
  | 'nie_podlega_weryfikacji'

export type StrengthLevel = 'wysoka' | 'srednia' | 'niska'

export type Citation = {
  n: number
  title: string
  publisher: string
  published_at: string | null
  url: string
  quote: string
  archival: boolean
}

export type ClaimResult = {
  claim_id: string
  text: string
  verdict: Verdict
  explanation_pl: string
  strength: { level: StrengthLevel } | null
  missing_context_pl: string | null
  conflicts: { summary_pl: string; citations: number[] }[]
  unresolved_pl: string | null
  citations: Citation[]
  context_notices: { kind: string; text_pl: string }[]
}

export type CheckResult = {
  check_id: string
  status: CheckStatus
  status_message_pl: string | null
  claims: ClaimResult[]
  extracted_text_pl: string | null
  input_notices_pl: string[]
  limitations_pl: string[]
  case: { message_pl: string } | null
}

export type CheckState =
  | { phase: 'pending'; requestId: string; label: string }
  | { phase: 'done'; requestId: string; label: string; result: CheckResult; serverUrl: string }
  | { phase: 'error'; requestId: string; label: string; message: string }

export type ExtensionMessage = { kind: 'start_check'; input: CheckInput; label: string }
