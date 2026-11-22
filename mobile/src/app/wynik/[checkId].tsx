import { useLocalSearchParams } from 'expo-router'
import { useEffect, useState } from 'react'
import { ActivityIndicator, ScrollView, StyleSheet } from 'react-native'

import { getCheck } from '@/api/client'
import type { CheckResult } from '@/api/types'
import { Notice } from '@/components/Notice'
import { ResultView } from '@/components/ResultView'
import { COLORS, SPACING } from '@/constants/tokens'
import { getCachedResult } from '@/lib/resultCache'
import { getServerUrl } from '@/lib/settings'

export default function ResultScreen() {
  const { checkId } = useLocalSearchParams<{ checkId: string }>()
  const [result, setResult] = useState<CheckResult | null>(() => getCachedResult(checkId) ?? null)
  const [serverUrl, setServerUrl] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    void getServerUrl().then(setServerUrl)
    if (getCachedResult(checkId)) return
    getCheck(checkId)
      .then(setResult)
      .catch((error: unknown) => setErrorMessage(error instanceof Error ? error.message : String(error)))
  }, [checkId])

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {errorMessage ? <Notice text={errorMessage} /> : null}
      {result && serverUrl ? (
        <ResultView result={result} webResultUrl={`${serverUrl}/wynik/${encodeURIComponent(result.check_id)}`} />
      ) : null}
      {!result && !errorMessage ? <ActivityIndicator color={COLORS.system} /> : null}
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { padding: SPACING[4], gap: SPACING[4] },
})
