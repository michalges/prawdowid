import { Linking, Pressable, StyleSheet, Text, View } from 'react-native'

import type { Citation, ClaimResult } from '@/api/types'
import { NO_STRENGTH_VERDICTS, STRENGTH_LABELS } from '@/constants/labels'
import { COLORS, RADIUS, SPACING, VERDICT_COLORS } from '@/constants/tokens'

import { Notice } from './Notice'
import { VerdictBadge } from './VerdictBadge'

export function ClaimCard({ claim }: { claim: ClaimResult }) {
  const isStrengthShown = claim.strength && !NO_STRENGTH_VERDICTS.has(claim.verdict)
  return (
    <View style={[styles.card, { borderLeftColor: VERDICT_COLORS[claim.verdict].fg }]}>
      <VerdictBadge verdict={claim.verdict} />
      <Text style={styles.claimText}>{claim.text}</Text>
      <Text style={styles.body}>{claim.explanation_pl}</Text>
      {isStrengthShown && claim.strength ? (
        <Text style={styles.meta}>Siła dowodów: {STRENGTH_LABELS[claim.strength.level]}</Text>
      ) : null}
      {claim.missing_context_pl ? (
        <Notice tone="warning" title="Brakujący kontekst" text={claim.missing_context_pl} />
      ) : null}
      {claim.conflicts.map((conflict) => (
        <Notice key={conflict.summary_pl} tone="warning" text={conflict.summary_pl} />
      ))}
      {claim.unresolved_pl ? <Text style={styles.meta}>{claim.unresolved_pl}</Text> : null}
      {claim.context_notices.map((notice) => (
        <Notice key={notice.text_pl} text={notice.text_pl} />
      ))}
      {claim.citations.length ? (
        <View style={styles.citations}>
          <Text style={styles.sectionTitle}>Źródła</Text>
          {claim.citations.map((citation) => (
            <CitationItem key={citation.n} citation={citation} />
          ))}
        </View>
      ) : null}
    </View>
  )
}

function CitationItem({ citation }: { citation: Citation }) {
  const details = [citation.published_at ?? 'brak daty', citation.archival ? 'archiwalne' : null]
    .filter(Boolean)
    .join(' · ')
  return (
    <View style={styles.citation}>
      <Text style={styles.quote}>„{citation.quote}”</Text>
      <Pressable accessibilityRole="link" onPress={() => void Linking.openURL(citation.url)}>
        <Text style={styles.meta}>
          [{citation.n}] <Text style={styles.link}>{citation.publisher || citation.title}</Text> · {details}
        </Text>
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  card: {
    gap: SPACING[2],
    padding: SPACING[3],
    borderWidth: 1,
    borderLeftWidth: 4,
    borderColor: COLORS.border,
    borderRadius: RADIUS,
    backgroundColor: COLORS.surface,
  },
  claimText: { fontSize: 17, lineHeight: 24, fontWeight: '700', color: COLORS.ink },
  body: { fontSize: 16, lineHeight: 24, color: COLORS.ink },
  meta: { fontSize: 14, lineHeight: 20, color: COLORS.inkSubtle },
  sectionTitle: { fontSize: 13, fontWeight: '700', color: COLORS.inkMuted, textTransform: 'uppercase' },
  citations: { gap: SPACING[3], marginTop: SPACING[1] },
  citation: { gap: SPACING[1] },
  quote: {
    fontFamily: 'serif',
    fontSize: 16,
    lineHeight: 25,
    color: COLORS.ink,
    paddingLeft: SPACING[2],
    borderLeftWidth: 2,
    borderLeftColor: COLORS.border,
  },
  link: { color: COLORS.brand, textDecorationLine: 'underline' },
})
