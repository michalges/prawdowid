import { Linking, Pressable, StyleSheet, Text, View } from 'react-native'

import type { CheckResult } from '@/api/types'
import { STATUS_TITLES, TRANSPARENCY_NOTE } from '@/constants/labels'
import { COLORS, SPACING } from '@/constants/tokens'

import { ClaimCard } from './ClaimCard'
import { Notice } from './Notice'

export function ResultView({ result, webResultUrl }: { result: CheckResult; webResultUrl: string }) {
  return (
    <View style={styles.container}>
      {result.status !== 'ok' ? (
        <Notice title={STATUS_TITLES[result.status]} text={result.status_message_pl ?? ''} />
      ) : null}
      {result.input_notices_pl.map((notice) => (
        <Notice key={notice} text={notice} />
      ))}
      {result.extracted_text_pl ? (
        <View style={styles.extracted}>
          <Text style={styles.sectionTitle}>Odczytany tekst</Text>
          <Text style={styles.extractedText}>{result.extracted_text_pl}</Text>
        </View>
      ) : null}
      {result.claims.map((claim) => (
        <ClaimCard key={claim.claim_id} claim={claim} />
      ))}
      {result.case ? <Notice text={result.case.message_pl} /> : null}
      {result.limitations_pl.map((limitation) => (
        <Text key={limitation} style={styles.meta}>
          {limitation}
        </Text>
      ))}
      <Pressable accessibilityRole="link" onPress={() => void Linking.openURL(webResultUrl)}>
        <Text style={styles.link}>Pokaż w przeglądarce</Text>
      </Pressable>
      <Text style={styles.meta}>{TRANSPARENCY_NOTE}</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { gap: SPACING[3] },
  sectionTitle: { fontSize: 13, fontWeight: '700', color: COLORS.inkMuted, textTransform: 'uppercase' },
  extracted: { gap: SPACING[1], padding: SPACING[3], backgroundColor: COLORS.surfaceSubtle, borderRadius: 8 },
  extractedText: { fontSize: 15, lineHeight: 22, color: COLORS.inkMuted },
  meta: { fontSize: 14, lineHeight: 20, color: COLORS.inkSubtle },
  link: { fontSize: 16, fontWeight: '600', color: COLORS.brand, textDecorationLine: 'underline' },
})
