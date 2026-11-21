import { Archive, Info, TriangleAlert } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

type Tone = 'system' | 'warning' | 'neutral'

const TONES: Record<Tone, { Icon: LucideIcon; className: string }> = {
  system: { Icon: Info, className: 'bg-system-bg text-system' },
  warning: { Icon: TriangleAlert, className: 'bg-warning-bg text-warning' },
  neutral: { Icon: Archive, className: 'bg-verdict-insufficient-bg text-verdict-insufficient' },
}

export function Notice({
  tone,
  title,
  children,
  icon,
}: {
  tone: Tone
  title?: string
  children: ReactNode
  icon?: LucideIcon
}) {
  const { Icon: DefaultIcon, className } = TONES[tone]
  const Icon = icon ?? DefaultIcon
  return (
    <div className={`flex gap-3 rounded-md px-4 py-3 ${className}`}>
      <Icon aria-hidden className="mt-0.5 size-4.5 shrink-0" />
      <div className="text-body-sm">
        {title && <p className="font-semibold">{title}</p>}
        <div className="text-ink">{children}</div>
      </div>
    </div>
  )
}
