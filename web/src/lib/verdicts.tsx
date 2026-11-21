import { CircleCheck, CircleDashed, CircleX, MessageSquare, TriangleAlert } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import type { StrengthLevel, Verdict } from '../api/types'

type VerdictStyle = {
  Icon: LucideIcon
  textClass: string
  backgroundClass: string
  borderClass: string
}

/** DESIGN.md §2.3: every verdict is label + distinct icon shape + colour. */
export const VERDICT_STYLES: Record<Verdict, VerdictStyle> = {
  potwierdzone: {
    Icon: CircleCheck,
    textClass: 'text-verdict-true',
    backgroundClass: 'bg-verdict-true-bg',
    borderClass: 'border-verdict-true',
  },
  falszywe: {
    Icon: CircleX,
    textClass: 'text-verdict-false',
    backgroundClass: 'bg-verdict-false-bg',
    borderClass: 'border-verdict-false',
  },
  wprowadzajace_w_blad: {
    Icon: TriangleAlert,
    textClass: 'text-verdict-misleading',
    backgroundClass: 'bg-verdict-misleading-bg',
    borderClass: 'border-verdict-misleading',
  },
  brak_wystarczajacych_dowodow: {
    Icon: CircleDashed,
    textClass: 'text-verdict-insufficient',
    backgroundClass: 'bg-verdict-insufficient-bg',
    borderClass: 'border-verdict-insufficient',
  },
  nie_podlega_weryfikacji: {
    Icon: MessageSquare,
    textClass: 'text-verdict-unverifiable',
    backgroundClass: 'bg-verdict-unverifiable-bg',
    borderClass: 'border-verdict-unverifiable',
  },
}

export const STRENGTH_STEPS: Record<StrengthLevel, number> = { wysoka: 3, srednia: 2, niska: 1 }
