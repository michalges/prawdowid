import { StyleSheet, Text, View } from 'react-native'

import type { Verdict } from '@/api/types'
import { VERDICT_LABELS } from '@/constants/labels'
import { SPACING, VERDICT_COLORS } from '@/constants/tokens'

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  const { fg, bg } = VERDICT_COLORS[verdict]
  const { label, symbol } = VERDICT_LABELS[verdict]
  return (
    <View style={[styles.badge, { backgroundColor: bg }]} accessibilityLabel={`Wynik: ${label}`}>
      <View style={[styles.symbol, { backgroundColor: fg }]} importantForAccessibility="no-hide-descendants">
        <Text style={styles.symbolText}>{symbol}</Text>
      </View>
      <Text style={[styles.label, { color: fg }]}>{label}</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: SPACING[2],
    paddingVertical: SPACING[1],
    paddingLeft: SPACING[1],
    paddingRight: SPACING[3],
    borderRadius: 999,
  },
  symbol: { width: 22, height: 22, borderRadius: 11, alignItems: 'center', justifyContent: 'center' },
  symbolText: { color: '#ffffff', fontSize: 13, fontWeight: '700' },
  label: { fontSize: 14, fontWeight: '700' },
})
