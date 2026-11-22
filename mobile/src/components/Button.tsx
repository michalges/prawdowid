import { Pressable, StyleSheet, Text } from 'react-native'

import { COLORS, RADIUS, SPACING } from '@/constants/tokens'

export function Button({
  label,
  onPress,
  variant = 'primary',
  isDisabled = false,
}: {
  label: string
  onPress: () => void
  variant?: 'primary' | 'secondary'
  isDisabled?: boolean
}) {
  const isPrimary = variant === 'primary'
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: isDisabled }}
      disabled={isDisabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.base,
        isPrimary ? styles.primary : styles.secondary,
        pressed && (isPrimary ? styles.primaryPressed : styles.secondaryPressed),
        isDisabled && styles.disabled,
      ]}
    >
      <Text style={[styles.label, isPrimary && styles.primaryLabel]}>{label}</Text>
    </Pressable>
  )
}

const styles = StyleSheet.create({
  base: {
    minHeight: 48,
    paddingHorizontal: SPACING[4],
    paddingVertical: SPACING[3],
    borderRadius: RADIUS,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    flexGrow: 1,
  },
  primary: { backgroundColor: COLORS.brand, borderColor: COLORS.brand },
  primaryPressed: { backgroundColor: COLORS.brandPressed },
  secondary: { backgroundColor: COLORS.surface, borderColor: COLORS.borderControl },
  secondaryPressed: { backgroundColor: COLORS.surfaceSubtle },
  disabled: { opacity: 0.6 },
  label: { fontSize: 16, fontWeight: '600', color: COLORS.ink },
  primaryLabel: { color: COLORS.inkInverse },
})
