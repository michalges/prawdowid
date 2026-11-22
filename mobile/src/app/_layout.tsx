import { Stack } from 'expo-router'
import { StatusBar } from 'expo-status-bar'

import { COLORS } from '@/constants/tokens'

export default function RootLayout() {
  return (
    <>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerTintColor: COLORS.ink,
          headerStyle: { backgroundColor: COLORS.surface },
          contentStyle: { backgroundColor: COLORS.surface },
        }}
      >
        <Stack.Screen name="index" options={{ title: 'Prawdowid' }} />
        <Stack.Screen name="wynik/[checkId]" options={{ title: 'Wynik sprawdzenia' }} />
        <Stack.Screen name="historia" options={{ title: 'Historia sprawdzeń' }} />
        <Stack.Screen name="ustawienia" options={{ title: 'Ustawienia' }} />
      </Stack>
    </>
  )
}
