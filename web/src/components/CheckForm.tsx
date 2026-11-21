import { ArrowUp, ImagePlus, X } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'

import type { CheckInput } from '../api/types'

const MAX_TEXT_CHARS = 10_000
const MAX_IMAGE_BYTES = 5 * 1024 * 1024
const URL_ONLY = /^\s*https?:\/\/\S+\s*$/i

type SelectedImage = { name: string; dataUrl: string }

function readAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.addEventListener('load', () => resolve(String(reader.result)))
    reader.addEventListener('error', () => reject(reader.error))
    reader.readAsDataURL(file)
  })
}

function getCheckInput(text: string, image: SelectedImage | null): CheckInput {
  if (image) return { type: 'image', image_b64: image.dataUrl, text: text.trim() || undefined }
  if (URL_ONLY.test(text)) return { type: 'url', url: text.trim() }
  return { type: 'text', text: text.trim() }
}

/** Chat-style composer: Enter sends, Shift+Enter adds a new line. */
export function CheckForm({
  isBusy,
  draft,
  onDraftChange,
  onSubmit,
}: {
  isBusy: boolean
  draft: string
  onDraftChange: (text: string) => void
  onSubmit: (input: CheckInput, label: string) => void
}) {
  const [image, setImage] = useState<SelectedImage | null>(null)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = !isBusy && (draft.trim().length > 0 || image !== null) && draft.length <= MAX_TEXT_CHARS

  async function selectImage(file: File | undefined) {
    if (!file) return
    if (!file.type.startsWith('image/')) return setError('Wybierz plik obrazu (PNG, JPG, WEBP).')
    if (file.size > MAX_IMAGE_BYTES) return setError('Obraz jest za duży. Maksymalnie 5 MB.')
    setError(null)
    setImage({ name: file.name, dataUrl: await readAsDataUrl(file) })
  }

  function submit(event?: FormEvent) {
    event?.preventDefault()
    if (!canSubmit) return
    onSubmit(getCheckInput(draft, image), draft.trim() || `🖼 ${image?.name ?? 'Zrzut ekranu'}`)
    onDraftChange('')
    setImage(null)
  }

  function submitOnEnter(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-2">
      <label htmlFor="tresc-zgloszenia" className="sr-only">
        Co chcesz sprawdzić?
      </label>
      <div className="rounded-lg border border-border-control bg-surface shadow-card focus-within:border-brand-600 focus-within:shadow-focus">
        {image && (
          <div className="flex px-3 pt-3">
            <span className="inline-flex items-center gap-2 rounded-md bg-surface-subtle pl-3 text-body-sm text-ink">
              <ImagePlus aria-hidden className="size-4" />
              <span className="max-w-56 truncate">{image.name}</span>
              <button
                type="button"
                onClick={() => setImage(null)}
                className="inline-flex size-11 items-center justify-center rounded-md hover:bg-surface-sunken"
                aria-label="Usuń obraz"
              >
                <X aria-hidden className="size-4" />
              </button>
            </span>
          </div>
        )}
        <div className="flex items-end gap-1 p-2">
          <input
            type="file"
            accept="image/*"
            className="sr-only"
            id="zrzut-ekranu"
            onChange={(event) => {
              void selectImage(event.target.files?.[0])
              event.target.value = ''
            }}
          />
          <label
            htmlFor="zrzut-ekranu"
            title="Dodaj zrzut ekranu"
            className="inline-flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-md text-ink-muted hover:bg-surface-subtle hover:text-ink"
          >
            <ImagePlus aria-hidden className="size-5" />
            <span className="sr-only">Dodaj zrzut ekranu</span>
          </label>
          <textarea
            id="tresc-zgloszenia"
            value={draft}
            onChange={(event) => onDraftChange(event.target.value)}
            onKeyDown={submitOnEnter}
            rows={Math.min(Math.max(draft.split('\n').length, 1), 8)}
            maxLength={MAX_TEXT_CHARS}
            placeholder="Wklej wiadomość, link albo dodaj zrzut ekranu…"
            aria-describedby="tresc-pomoc"
            className="max-h-60 min-h-11 flex-1 resize-none bg-transparent px-2 py-2.5 text-body text-ink placeholder:text-ink-subtle focus:outline-none"
          />
          <button
            type="submit"
            disabled={!canSubmit}
            className="inline-flex min-h-11 shrink-0 items-center gap-2 rounded-md bg-brand-600 px-4 text-body font-semibold text-ink-inverse hover:bg-brand-700 active:bg-brand-800 disabled:cursor-not-allowed disabled:bg-surface-sunken disabled:text-ink-subtle"
          >
            <ArrowUp aria-hidden className="size-4" />
            {isBusy ? 'Sprawdzamy…' : 'Sprawdź'}
          </button>
        </div>
      </div>
      <p id="tresc-pomoc" className="sr-only">
        Enter wysyła, Shift+Enter dodaje nową linię. Możesz wkleić kilka zdań naraz.
      </p>
      {error && (
        <p role="alert" className="text-body-sm text-warning">
          {error}
        </p>
      )}
    </form>
  )
}
