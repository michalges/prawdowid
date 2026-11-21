import type { CheckState } from './types.js'

const STATE_KEY = 'checkState'

export async function getCheckState(): Promise<CheckState | null> {
  const stored = await chrome.storage.session.get(STATE_KEY)
  return (stored[STATE_KEY] as CheckState | undefined) ?? null
}

export async function setCheckState(state: CheckState | null): Promise<void> {
  if (state === null) await chrome.storage.session.remove(STATE_KEY)
  else await chrome.storage.session.set({ [STATE_KEY]: state })
}

export function onCheckStateChange(listener: (state: CheckState | null) => void): void {
  chrome.storage.session.onChanged.addListener((changes) => {
    const change = changes[STATE_KEY]
    if (change) listener((change.newValue as CheckState | undefined) ?? null)
  })
}
