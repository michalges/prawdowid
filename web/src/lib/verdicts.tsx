import { CircleCheck, CircleDashed, CircleX, MessageSquare, TriangleAlert } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import type { StrengthLevel, Verdict } from '../api/types'

type VerdictStyle = {
  label: string
  description: string
  Icon: LucideIcon
  textClass: string
  backgroundClass: string
  borderClass: string
}

/** DESIGN.md §2.3: every verdict is label + distinct icon shape + colour. */
export const VERDICT_STYLES: Record<Verdict, VerdictStyle> = {
  potwierdzone: {
    label: 'Potwierdzone',
    description: 'Źródła wprost potwierdzają to twierdzenie.',
    Icon: CircleCheck,
    textClass: 'text-verdict-true',
    backgroundClass: 'bg-verdict-true-bg',
    borderClass: 'border-verdict-true',
  },
  falszywe: {
    label: 'Fałszywe',
    description: 'Źródła wprost przeczą temu twierdzeniu.',
    Icon: CircleX,
    textClass: 'text-verdict-false',
    backgroundClass: 'bg-verdict-false-bg',
    borderClass: 'border-verdict-false',
  },
  wprowadzajace_w_blad: {
    label: 'Wprowadzające w błąd',
    description: 'Prawdziwe elementy prowadzą do złego wniosku albo brakuje ważnego kontekstu.',
    Icon: TriangleAlert,
    textClass: 'text-verdict-misleading',
    backgroundClass: 'bg-verdict-misleading-bg',
    borderClass: 'border-verdict-misleading',
  },
  brak_wystarczajacych_dowodow: {
    label: 'Brak wystarczających dowodów',
    description: 'Nasze źródła nie pozwalają tego rozstrzygnąć. Nie zgadujemy.',
    Icon: CircleDashed,
    textClass: 'text-verdict-insufficient',
    backgroundClass: 'bg-verdict-insufficient-bg',
    borderClass: 'border-verdict-insufficient',
  },
  nie_podlega_weryfikacji: {
    label: 'Nie podlega weryfikacji',
    description: 'To opinia, ocena albo przewidywanie, a nie fakt do sprawdzenia.',
    Icon: MessageSquare,
    textClass: 'text-verdict-unverifiable',
    backgroundClass: 'bg-verdict-unverifiable-bg',
    borderClass: 'border-verdict-unverifiable',
  },
}

export const STRENGTH_LABELS: Record<StrengthLevel, string> = {
  wysoka: 'wysoka',
  srednia: 'średnia',
  niska: 'niska',
}

export const STRENGTH_STEPS: Record<StrengthLevel, number> = { wysoka: 3, srednia: 2, niska: 1 }

export const SOURCE_TYPE_LABELS = {
  official_primary: 'źródło urzędowe',
  fact_check: 'weryfikator faktów',
  disinfo_db: 'baza dezinformacji',
  media_reference: 'media',
} as const
