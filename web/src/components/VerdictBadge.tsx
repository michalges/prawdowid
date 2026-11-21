import type { Verdict } from '../api/types'
import { useMessages } from '../lib/i18n'
import { VERDICT_STYLES } from '../lib/verdicts'

export function VerdictBadge({ verdict, size = 'md' }: { verdict: Verdict; size?: 'sm' | 'md' }) {
  const { label } = useMessages().verdicts[verdict]
  const { Icon, textClass, backgroundClass } = VERDICT_STYLES[verdict]
  const sizeClass = size === 'sm' ? 'gap-1 px-2 py-1 text-label' : 'gap-2 px-3 py-1.5 text-body-sm font-semibold'
  return (
    <span className={`inline-flex items-center rounded-md ${sizeClass} ${textClass} ${backgroundClass}`}>
      <Icon aria-hidden className={size === 'sm' ? 'size-3.5' : 'size-4.5'} strokeWidth={2.25} />
      {label}
    </span>
  )
}
