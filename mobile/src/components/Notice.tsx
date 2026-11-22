import { StyleSheet, Text, View } from 'react-native'

import { COLORS, RADIUS, SPACING } from '@/constants/tokens'

export function Notice({
  text,
  title,
  tone = 'system',
}: {
  text: string
  title?: string
  tone?: 'system' | 'warning'
}) {
  const color = tone === 'system' ? COLORS.system : COLORS.warning
  return (
    <View style={[styles.box, { backgroundColor: tone === 'system' ? COLORS.systemBg : COLORS.warningBg }]}>
      {title ? <Text style={[styles.title, { color }]}>{title}</Text> : null}
      <Text style={[styles.text, { color }]}>{text}</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  box: { padding: SPACING[3], borderRadius: RADIUS, gap: SPACING[1] },
  title: { fontSize: 15, fontWeight: '700' },
  text: { fontSize: 15, lineHeight: 22 },
})
