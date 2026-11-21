import type { ErrorComponentProps } from '@tanstack/react-router'

import { getErrorText } from '../lib/useApi'

export function RouteLoading({ text }: { text: string }) {
  return <output className="block text-body text-ink-muted">{text}</output>
}

export function RouteError({ error }: ErrorComponentProps) {
  return (
    <div role="alert" className="rounded-lg bg-system-bg p-6">
      <p className="text-body text-ink">{getErrorText(error)}</p>
    </div>
  )
}
