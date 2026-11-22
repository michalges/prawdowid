import { useEffect, useState } from 'react'
import { Alert, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'

import { deleteSession } from '@/api/client'
import { Button } from '@/components/Button'
import { COLORS, RADIUS, SPACING } from '@/constants/tokens'
import { clearHistory } from '@/lib/history'
import { clearSessionId } from '@/lib/session'
import { getDefaultServerUrl, getNormalizedServerUrl, getServerUrl, setServerUrl } from '@/lib/settings'

export default function SettingsScreen() {
  const [serverInput, setServerInput] = useState('')
  const [serverStatus, setServerStatus] = useState<string | null>(null)
  const [deleteStatus, setDeleteStatus] = useState<string | null>(null)

  useEffect(() => {
    void getServerUrl().then(setServerInput)
  }, [])

  async function saveServer() {
    const serverUrl = getNormalizedServerUrl(serverInput)
    if (!serverUrl) {
      setServerStatus('Podaj adres zaczynający się od https:// lub http://.')
      return
    }
    await setServerUrl(serverUrl === getDefaultServerUrl() ? null : serverUrl)
    setServerInput(serverUrl)
    setServerStatus('Zapisano.')
  }

  async function deleteData() {
    try {
      await deleteSession()
      await clearSessionId()
      await clearHistory()
      setDeleteStatus('Usunęliśmy Twoje dane z serwera i z tego telefonu.')
    } catch (error) {
      setDeleteStatus(error instanceof Error ? error.message : String(error))
    }
  }

  function confirmDeleteData() {
    Alert.alert('Usunąć moje dane?', 'Usuniemy historię sprawdzeń z tego telefonu i z serwera Prawdowida.', [
      { text: 'Anuluj', style: 'cancel' },
      { text: 'Usuń', style: 'destructive', onPress: () => void deleteData() },
    ])
  }

  return (
    <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
      <View style={styles.section}>
        <Text style={styles.heading}>Serwer</Text>
        <Text style={styles.meta}>Adres serwisu Prawdowid (ten sam, co strona WWW).</Text>
        <TextInput
          accessibilityLabel="Adres serwera"
          style={styles.input}
          value={serverInput}
          onChangeText={setServerInput}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
        />
        <Button label="Zapisz" onPress={() => void saveServer()} />
        {serverStatus ? <Text style={styles.meta}>{serverStatus}</Text> : null}
      </View>
      <View style={styles.section}>
        <Text style={styles.heading}>Twoje dane</Text>
        <Text style={styles.body}>
          Treść trafia na serwer Prawdowida dopiero po naciśnięciu „Sprawdź”. Dane osobowe są maskowane przed analizą, a
          sprawdzenia są usuwane po 30 dniach.
        </Text>
        <Button label="Usuń moje dane" variant="secondary" onPress={confirmDeleteData} />
        {deleteStatus ? <Text style={styles.meta}>{deleteStatus}</Text> : null}
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { padding: SPACING[4], gap: SPACING[8] },
  section: { gap: SPACING[3] },
  heading: { fontSize: 20, lineHeight: 28, fontWeight: '700', color: COLORS.ink },
  body: { fontSize: 16, lineHeight: 24, color: COLORS.ink },
  meta: { fontSize: 14, lineHeight: 20, color: COLORS.inkSubtle },
  input: {
    padding: SPACING[3],
    fontSize: 16,
    color: COLORS.ink,
    borderWidth: 1,
    borderColor: COLORS.borderControl,
    borderRadius: RADIUS,
  },
})
