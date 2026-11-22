import type { Verdict } from '@/api/types'

/** docs/design/tokens.json; rules in docs/DESIGN.md. */
export const COLORS = {
  brand: '#d4213d',
  brandPressed: '#b01a33',
  surface: '#ffffff',
  surfaceSubtle: '#f6f6f8',
  border: '#e3e4e8',
  borderControl: '#858b97',
  ink: '#16181d',
  inkMuted: '#4d5360',
  inkSubtle: '#6b7180',
  inkInverse: '#ffffff',
  system: '#1f5fae',
  systemBg: '#eaf2fb',
  warning: '#8a5300',
  warningBg: '#fdf2d8',
}

export const VERDICT_COLORS: Record<Verdict, { fg: string; bg: string }> = {
  potwierdzone: { fg: '#0b6e4f', bg: '#e7f4ee' },
  falszywe: { fg: '#8a1538', bg: '#fbe9ee' },
  wprowadzajace_w_blad: { fg: '#8a5300', bg: '#fdf2d8' },
  brak_wystarczajacych_dowodow: { fg: '#475467', bg: '#eef0f3' },
  nie_podlega_weryfikacji: { fg: '#4a4594', bg: '#eeedf8' },
}

export const SPACING = { 1: 4, 2: 8, 3: 12, 4: 16, 6: 24, 8: 32 }
export const RADIUS = 8
