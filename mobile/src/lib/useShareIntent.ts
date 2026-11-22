import { useEffect, useEffectEvent } from 'react'

import ShareIntent, { type SharePayload } from '../../modules/share-intent'

/** Calls `onShare` for content shared into the app (Share menu or text-selection menu), cold or warm start. */
export function useShareIntent(onShare: (share: SharePayload) => void): void {
  const handleShare = useEffectEvent(onShare)

  useEffect(() => {
    if (!ShareIntent) return
    let isMounted = true
    void ShareIntent.getInitialShare().then((initial) => {
      if (initial && isMounted) handleShare(initial)
    })
    const subscription = ShareIntent.addListener('onShare', (share) => handleShare(share))
    return () => {
      isMounted = false
      subscription.remove()
    }
  }, [])
}
