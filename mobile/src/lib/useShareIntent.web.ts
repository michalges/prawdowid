import { useEffect, useEffectEvent } from 'react'

import type { SharePayload } from '../../modules/share-intent'

/**
 * Web build: reads Web Share Target-style query params (`?title=&text=&url=`) once, so shared content
 * lands on the same confirmation screen as on Android.
 */
export function useShareIntent(onShare: (share: SharePayload) => void): void {
  const handleShare = useEffectEvent(onShare)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const text = [params.get('text'), params.get('url')].filter(Boolean).join('\n').trim()
    if (!text) return
    window.history.replaceState(null, '', window.location.pathname)
    handleShare({ kind: 'text', text, subject: params.get('title'), source: 'share' })
  }, [])
}
