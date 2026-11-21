import { createElement, createExternalLink, getRequiredElement } from './dom.js'
import { getLabel, getTextOrUrlInput, isCheckableUrl } from './input.js'
import { ERRORS, NO_STRENGTH_VERDICTS, STATUS_TITLES, STRENGTH_LABELS, VERDICT_LABELS } from './labels.js'
import { getCheckState, onCheckStateChange } from './state.js'
import type { CheckInput, CheckResult, CheckState, Citation, ClaimResult, ExtensionMessage } from './types.js'

const MAX_CITATIONS_SHOWN = 3
const SCREENSHOT_JPEG_QUALITY = 85

const form = getRequiredElement('check-form', HTMLFormElement)
const textInput = getRequiredElement('check-text', HTMLTextAreaElement)
const submitButton = getRequiredElement('check-submit', HTMLButtonElement)
const pageButton = getRequiredElement('check-page', HTMLButtonElement)
const screenshotButton = getRequiredElement('check-screenshot', HTMLButtonElement)
const resultContainer = getRequiredElement('result', HTMLElement)
const optionsLink = getRequiredElement('open-options', HTMLAnchorElement)

void chrome.action.setBadgeText({ text: '' })
void getCheckState().then(renderState)
onCheckStateChange(renderState)

form.addEventListener('submit', (event) => {
  event.preventDefault()
  const input = getTextOrUrlInput(textInput.value)
  if (input) startCheck(input)
})

textInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) form.requestSubmit()
})

pageButton.addEventListener('click', async () => {
  const tab = await getActiveTab()
  if (isCheckableUrl(tab?.url)) startCheck({ type: 'url', url: tab.url })
  else renderError(ERRORS.unreadablePage)
})

screenshotButton.addEventListener('click', async () => {
  try {
    const dataUrl = await chrome.tabs.captureVisibleTab({ format: 'jpeg', quality: SCREENSHOT_JPEG_QUALITY })
    startCheck({ type: 'image', image_b64: dataUrl.slice(dataUrl.indexOf(',') + 1) })
  } catch {
    renderError(ERRORS.screenshotFailed)
  }
})

optionsLink.addEventListener('click', (event) => {
  event.preventDefault()
  void chrome.runtime.openOptionsPage()
})

async function getActiveTab(): Promise<chrome.tabs.Tab | undefined> {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
  return tab
}

function startCheck(input: CheckInput): void {
  const message: ExtensionMessage = { kind: 'start_check', input, label: getLabel(input) }
  void chrome.runtime.sendMessage(message)
}

function renderState(state: CheckState | null): void {
  const isPending = state?.phase === 'pending'
  for (const button of [submitButton, pageButton, screenshotButton]) button.disabled = isPending
  if (!state) return resultContainer.replaceChildren()
  const labelElement = createElement('p', { className: 'checked-label', text: state.label })
  if (state.phase === 'pending') {
    return resultContainer.replaceChildren(
      labelElement,
      createElement('p', {
        className: 'notice notice-system',
        text: 'Sprawdzamy w źródłach… To może potrwać do minuty.',
      }),
    )
  }
  if (state.phase === 'error') return renderError(state.message, labelElement)
  resultContainer.replaceChildren(labelElement, ...getResultElements(state.result, state.serverUrl))
}

function renderError(message: string, labelElement: HTMLElement | null = null): void {
  resultContainer.replaceChildren(
    ...[labelElement, createElement('p', { className: 'notice notice-system', text: message })].filter(
      (element) => element !== null,
    ),
  )
}

function getResultElements(result: CheckResult, serverUrl: string): HTMLElement[] {
  const elements: HTMLElement[] = []
  if (result.status !== 'ok') {
    elements.push(
      createElement('div', { className: 'notice notice-system' }, [
        createElement('strong', { text: STATUS_TITLES[result.status] }),
        createElement('p', { text: result.status_message_pl ?? '' }),
      ]),
    )
  }
  for (const notice of result.input_notices_pl) {
    elements.push(createElement('p', { className: 'notice notice-system', text: notice }))
  }
  if (result.extracted_text_pl) {
    elements.push(
      createElement('details', { className: 'extracted' }, [
        createElement('summary', { text: 'Odczytany tekst' }),
        createElement('p', { text: result.extracted_text_pl }),
      ]),
    )
  }
  elements.push(...result.claims.map(getClaimElement))
  if (result.case)
    elements.push(createElement('p', { className: 'notice notice-system', text: result.case.message_pl }))
  for (const limitation of result.limitations_pl) {
    elements.push(createElement('p', { className: 'limitation', text: limitation }))
  }
  elements.push(
    createExternalLink(
      `${serverUrl}/wynik/${encodeURIComponent(result.check_id)}`,
      'Zobacz pełny wynik',
      'full-result',
    ),
  )
  return elements
}

function getClaimElement(claim: ClaimResult): HTMLElement {
  const verdict = VERDICT_LABELS[claim.verdict]
  const shownCitations = claim.citations.slice(0, MAX_CITATIONS_SHOWN)
  const hiddenCount = claim.citations.length - shownCitations.length
  return createElement('article', { className: `claim verdict-${claim.verdict}` }, [
    createElement('div', { className: 'verdict-badge' }, [
      createElement('span', {
        className: 'verdict-symbol',
        text: verdict.symbol,
        attributes: { 'aria-hidden': 'true' },
      }),
      createElement('span', { text: verdict.label }),
    ]),
    createElement('p', { className: 'claim-text', text: claim.text }),
    createElement('p', { text: claim.explanation_pl }),
    claim.strength && !NO_STRENGTH_VERDICTS.has(claim.verdict)
      ? createElement('p', { className: 'meta', text: `Siła dowodów: ${STRENGTH_LABELS[claim.strength.level]}` })
      : null,
    claim.missing_context_pl
      ? createElement('p', {
          className: 'notice notice-warning',
          text: `Brakujący kontekst: ${claim.missing_context_pl}`,
        })
      : null,
    ...claim.conflicts.map((conflict) =>
      createElement('p', { className: 'notice notice-warning', text: conflict.summary_pl }),
    ),
    claim.unresolved_pl ? createElement('p', { className: 'meta', text: claim.unresolved_pl }) : null,
    ...claim.context_notices.map((notice) =>
      createElement('p', { className: 'notice notice-system', text: notice.text_pl }),
    ),
    shownCitations.length
      ? createElement('ol', { className: 'citations' }, shownCitations.map(getCitationElement))
      : null,
    hiddenCount > 0
      ? createElement('p', { className: 'meta', text: `+${hiddenCount} więcej źródeł w pełnym wyniku` })
      : null,
  ])
}

function getCitationElement(citation: Citation): HTMLElement {
  const details = [citation.published_at ?? 'brak daty', citation.archival ? 'archiwalne' : null]
    .filter(Boolean)
    .join(' · ')
  return createElement('li', {}, [
    createElement('blockquote', { text: `„${citation.quote}”` }),
    createElement('p', { className: 'meta' }, [
      createElement('span', { text: `[${citation.n}] ` }),
      createExternalLink(citation.url, citation.publisher || citation.title),
      createElement('span', { text: ` · ${details}` }),
    ]),
  ])
}
