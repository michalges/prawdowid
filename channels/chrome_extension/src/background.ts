import { ApiError, postCheck } from './api.js'
import { getLabel, getTextOrUrlInput, isCheckableUrl } from './input.js'
import { ERRORS, MENU_TITLES } from './labels.js'
import { getServerUrl } from './settings.js'
import { getCheckState, setCheckState } from './state.js'
import type { CheckInput, ExtensionMessage } from './types.js'

const KEEPALIVE_INTERVAL_MS = 20_000
const BADGE_COLOUR = '#1f5fae'

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({ id: 'selection', title: MENU_TITLES.selection, contexts: ['selection'] })
    chrome.contextMenus.create({ id: 'link', title: MENU_TITLES.link, contexts: ['link'] })
    chrome.contextMenus.create({ id: 'page', title: MENU_TITLES.page, contexts: ['page'] })
  })
})

chrome.contextMenus.onClicked.addListener((info) => {
  const input = getContextMenuInput(info)
  if (!input) return
  openPopup()
  void runCheck(input, getLabel(input))
})

chrome.runtime.onMessage.addListener((message: ExtensionMessage) => {
  if (message.kind === 'start_check') void runCheck(message.input, message.label)
})

function getContextMenuInput(info: chrome.contextMenus.OnClickData): CheckInput | null {
  if (info.menuItemId === 'selection' && info.selectionText) return getTextOrUrlInput(info.selectionText)
  if (info.menuItemId === 'link' && isCheckableUrl(info.linkUrl)) return { type: 'url', url: info.linkUrl }
  if (info.menuItemId === 'page' && isCheckableUrl(info.pageUrl)) return { type: 'url', url: info.pageUrl }
  return null
}

/** Must run synchronously inside the click handler to keep the user gesture. */
function openPopup(): void {
  chrome.action.openPopup().catch(() => {
    // Not supported in this browser or window; the badge tells the user to open the popup.
  })
}

async function runCheck(input: CheckInput, label: string): Promise<void> {
  const requestId = crypto.randomUUID()
  await setCheckState({ phase: 'pending', requestId, label })
  await setBadge('…')
  const keepalive = setInterval(() => void chrome.runtime.getPlatformInfo(), KEEPALIVE_INTERVAL_MS)
  try {
    const serverUrl = await getServerUrl()
    const result = await postCheck(serverUrl, input)
    if (await isLatestRequest(requestId)) await setCheckState({ phase: 'done', requestId, label, result, serverUrl })
  } catch (error) {
    const message = error instanceof ApiError ? error.message : ERRORS.unavailable
    if (await isLatestRequest(requestId)) await setCheckState({ phase: 'error', requestId, label, message })
  } finally {
    clearInterval(keepalive)
    if (await isLatestRequest(requestId)) await setBadge('1')
  }
}

async function isLatestRequest(requestId: string): Promise<boolean> {
  return (await getCheckState())?.requestId === requestId
}

async function setBadge(text: string): Promise<void> {
  await chrome.action.setBadgeBackgroundColor({ color: BADGE_COLOUR })
  await chrome.action.setBadgeText({ text })
}
