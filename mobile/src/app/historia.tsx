import { router, useFocusEffect } from 'expo-router'
import { useState } from 'react'
import { FlatList, Pressable, StyleSheet, Text, View } from 'react-native'

import { STATUS_TITLES, VERDICT_LABELS } from '@/constants/labels'
import { COLORS, SPACING } from '@/constants/tokens'
import { getHistory, type HistoryEntry } from '@/lib/history'

function getSummary(entry: HistoryEntry): string {
  if (entry.status !== 'ok') return STATUS_TITLES[entry.status]
  if (!entry.verdicts.length) return 'bez oceny'
  return entry.verdicts.map((verdict) => VERDICT_LABELS[verdict].label).join(', ')
}

function Separator() {
  return <View style={styles.separator} />
}

export default function HistoryScreen() {
  const [entries, setEntries] = useState<HistoryEntry[]>([])

  useFocusEffect(() => {
    void getHistory().then(setEntries)
  })

  return (
    <FlatList
      contentContainerStyle={styles.container}
      data={entries}
      keyExtractor={(entry) => entry.checkId}
      ListHeaderComponent={
        <Text style={styles.meta}>
          Lista jest zapisana tylko na tym telefonie. Na serwerze sprawdzenia są usuwane po 30 dniach.
        </Text>
      }
      ListEmptyComponent={<Text style={styles.body}>Nie masz jeszcze żadnych sprawdzeń.</Text>}
      ItemSeparatorComponent={Separator}
      renderItem={({ item }) => (
        <Pressable
          accessibilityRole="button"
          style={styles.item}
          onPress={() => router.push({ pathname: '/wynik/[checkId]', params: { checkId: item.checkId } })}
        >
          <Text style={styles.body} numberOfLines={2}>
            {item.label}
          </Text>
          <Text style={styles.meta}>
            {new Date(item.createdAt).toLocaleString('pl-PL')} · {getSummary(item)}
          </Text>
        </Pressable>
      )}
    />
  )
}

const styles = StyleSheet.create({
  container: { padding: SPACING[4], gap: SPACING[3] },
  item: { paddingVertical: SPACING[2], gap: SPACING[1] },
  separator: { height: 1, backgroundColor: COLORS.border },
  body: { fontSize: 16, lineHeight: 24, color: COLORS.ink },
  meta: { fontSize: 14, lineHeight: 20, color: COLORS.inkSubtle },
})
