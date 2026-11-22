import * as ImagePicker from 'expo-image-picker'
import { Image } from 'expo-image'
import { router } from 'expo-router'
import { useState } from 'react'
import { ActivityIndicator, KeyboardAvoidingView, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'

import { postCheck } from '@/api/client'
import type { CheckInput } from '@/api/types'
import { Button } from '@/components/Button'
import { Notice } from '@/components/Notice'
import { TRANSPARENCY_NOTE } from '@/constants/labels'
import { COLORS, RADIUS, SPACING } from '@/constants/tokens'
import { addHistoryEntry } from '@/lib/history'
import { getImageBase64 } from '@/lib/image'
import { getLabel, getSharedText, getTextOrUrlInput } from '@/lib/input'
import { setCachedResult } from '@/lib/resultCache'
import { useShareIntent } from '@/lib/useShareIntent'

const MAX_TEXT_CHARS = 10_000

export default function CheckScreen() {
  const [text, setText] = useState('')
  const [imageUri, setImageUri] = useState<string | null>(null)
  const [isShared, setIsShared] = useState(false)
  const [isChecking, setIsChecking] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useShareIntent((share) => {
    if (router.canDismiss()) router.dismissAll()
    setErrorMessage(null)
    setIsShared(true)
    setImageUri(share.kind === 'image' ? share.uri : null)
    setText(share.kind === 'text' ? getSharedText(share.text, share.subject).slice(0, MAX_TEXT_CHARS) : '')
  })

  function resetForm() {
    setText('')
    setImageUri(null)
    setIsShared(false)
    setErrorMessage(null)
  }

  async function pickImage() {
    const picked = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 1 })
    if (picked.canceled || !picked.assets[0]) return
    setImageUri(picked.assets[0].uri)
    setErrorMessage(null)
  }

  async function getCheckInput(): Promise<CheckInput | null> {
    if (imageUri) return { type: 'image', image_b64: await getImageBase64(imageUri) }
    return getTextOrUrlInput(text)
  }

  async function submitCheck() {
    setIsChecking(true)
    setErrorMessage(null)
    try {
      const input = await getCheckInput()
      if (!input) return
      const result = await postCheck(input)
      setCachedResult(result)
      await addHistoryEntry(result, getLabel(input))
      resetForm()
      router.push({ pathname: '/wynik/[checkId]', params: { checkId: result.check_id } })
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : String(error))
    } finally {
      setIsChecking(false)
    }
  }

  const isSubmittable = !isChecking && (imageUri !== null || text.trim().length > 0)

  return (
    <KeyboardAvoidingView style={styles.flex} behavior="height">
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        {isShared ? (
          <Notice
            title="Sprawdź, co wyślemy"
            text="Ta treść przyszła z innej aplikacji. Możesz ją poprawić albo anulować. Nic nie zostało jeszcze wysłane."
          />
        ) : (
          <Text style={styles.intro}>
            Wklej informację, link albo wybierz zrzut ekranu. Sprawdzimy ją w oficjalnych źródłach.
          </Text>
        )}
        {imageUri ? (
          <View style={styles.imageBox}>
            <Image
              source={{ uri: imageUri }}
              style={styles.image}
              contentFit="contain"
              accessibilityLabel="Wybrany zrzut ekranu"
            />
            <Button label="Usuń obraz" variant="secondary" onPress={() => setImageUri(null)} isDisabled={isChecking} />
          </View>
        ) : (
          <TextInput
            accessibilityLabel="Tekst lub link do sprawdzenia"
            style={styles.input}
            multiline
            maxLength={MAX_TEXT_CHARS}
            placeholder="np. „Od stycznia ETIAS obowiązuje Polaków…”"
            placeholderTextColor={COLORS.inkSubtle}
            value={text}
            onChangeText={setText}
            editable={!isChecking}
            textAlignVertical="top"
          />
        )}
        {errorMessage ? <Notice text={errorMessage} /> : null}
        <Button
          label={isChecking ? 'Sprawdzamy…' : 'Sprawdź'}
          onPress={() => void submitCheck()}
          isDisabled={!isSubmittable}
        />
        {isChecking ? (
          <View style={styles.progress} accessibilityLiveRegion="polite">
            <ActivityIndicator color={COLORS.system} />
            <Text style={styles.meta}>Szukamy w źródłach. To może potrwać do minuty.</Text>
          </View>
        ) : null}
        <View style={styles.row}>
          {isShared ? (
            <Button label="Anuluj" variant="secondary" onPress={resetForm} isDisabled={isChecking} />
          ) : (
            <Button
              label="Wybierz zrzut ekranu"
              variant="secondary"
              onPress={() => void pickImage()}
              isDisabled={isChecking}
            />
          )}
        </View>
        <Text style={styles.meta}>
          W innych aplikacjach zaznacz tekst i wybierz „Sprawdź w Prawdowidzie” albo użyj „Udostępnij → Prawdowid”.
        </Text>
        <View style={styles.row}>
          <Button label="Historia" variant="secondary" onPress={() => router.push('/historia')} />
          <Button label="Ustawienia" variant="secondary" onPress={() => router.push('/ustawienia')} />
        </View>
        <Text style={styles.meta}>{TRANSPARENCY_NOTE}</Text>
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { padding: SPACING[4], gap: SPACING[4] },
  intro: { fontSize: 16, lineHeight: 24, color: COLORS.inkMuted },
  input: {
    minHeight: 140,
    padding: SPACING[3],
    fontSize: 16,
    lineHeight: 24,
    color: COLORS.ink,
    borderWidth: 1,
    borderColor: COLORS.borderControl,
    borderRadius: RADIUS,
  },
  imageBox: { gap: SPACING[2] },
  image: { width: '100%', height: 280, borderRadius: RADIUS, backgroundColor: COLORS.surfaceSubtle },
  progress: { flexDirection: 'row', alignItems: 'center', gap: SPACING[2] },
  row: { flexDirection: 'row', gap: SPACING[2] },
  meta: { fontSize: 14, lineHeight: 20, color: COLORS.inkSubtle },
})
