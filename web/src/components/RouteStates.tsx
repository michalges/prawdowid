import type { ErrorComponentProps } from '@tanstack/react-router'

import { useMessages } from '../lib/i18n'
import type { Messages } from '../locales/pl'
import { getErrorText } from '../lib/useApi'

export function RouteLoading({ what }: { what: keyof Messages['loading'] }) {
  const { loading } = useMessages()
  return <output className="block text-body text-ink-muted">{loading[what]}</output>
}

export function RouteError({ error }: ErrorComponentProps) {
  return (
    <div role="alert" className="rounded-lg bg-system-bg p-6">
      <p className="text-body text-ink">{getErrorText(error)}</p>
    </div>
  )
}
