import { ImagePlus, X } from 'lucide-react'
import { useRef, useState } from 'react'
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

export function CheckForm({
  isBusy,
  draft: text,
  onDraftChange: setText,
  onSubmit,
}: {
  isBusy: boolean
  draft: string
  onDraftChange: (text: string) => void
  onSubmit: (input: CheckInput, label: string) => void
}) {
  const [image, setImage] = useState<SelectedImage | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  const canSubmit = !isBusy && (text.trim().length > 0 || image !== null) && text.length <= MAX_TEXT_CHARS

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
    onSubmit(getCheckInput(text, image), text.trim() || image?.name || 'Zrzut ekranu')
    setText('')
    setImage(null)
  }

  function submitOnShortcut(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) submit()
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <label htmlFor="tresc-zgloszenia" className="sr-only">
        Co chcesz sprawdzić?
      </label>
      <div className="rounded-lg border border-border-control bg-surface shadow-card focus-within:border-brand-600 focus-within:shadow-focus">
        <textarea
          id="tresc-zgloszenia"
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={submitOnShortcut}
          rows={3}
          maxLength={MAX_TEXT_CHARS}
          placeholder="Wklej treść wiadomości, posta albo link do artykułu…"
          aria-describedby="tresc-pomoc"
          className="block w-full resize-y rounded-t-lg bg-transparent px-4 py-3 text-body text-ink placeholder:text-ink-subtle focus:outline-none"
        />
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border px-2 py-2">
          <div className="flex items-center gap-2">
            <input
              ref={fileInput}
              type="file"
              accept="image/*"
              className="sr-only"
              id="zrzut-ekranu"
              onChange={(event) => selectImage(event.target.files?.[0])}
            />
            {image ? (
              <span className="inline-flex min-h-11 items-center gap-2 rounded-md bg-surface-subtle pl-3 text-body-sm text-ink">
                <ImagePlus aria-hidden className="size-4" />
                <span className="max-w-48 truncate">{image.name}</span>
                <button
                  type="button"
                  onClick={() => setImage(null)}
                  className="inline-flex size-11 items-center justify-center rounded-md hover:bg-surface-sunken"
                  aria-label="Usuń obraz"
                >
                  <X aria-hidden className="size-4" />
                </button>
              </span>
            ) : (
              <label
                htmlFor="zrzut-ekranu"
                className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-md px-3 text-body-sm font-medium text-ink-muted hover:bg-surface-subtle hover:text-ink"
              >
                <ImagePlus aria-hidden className="size-4" />
                Dodaj zrzut ekranu
              </label>
            )}
            <span className="font-mono text-meta text-ink-subtle">
              {text.length}/{MAX_TEXT_CHARS}
            </span>
          </div>
          <button
            type="submit"
            disabled={!canSubmit}
            className="inline-flex min-h-11 items-center rounded-md bg-brand-600 px-6 text-body font-semibold text-ink-inverse hover:bg-brand-700 active:bg-brand-800 disabled:cursor-not-allowed disabled:bg-surface-sunken disabled:text-ink-subtle"
          >
            {isBusy ? 'Sprawdzamy…' : 'Sprawdź'}
          </button>
        </div>
      </div>
      <p id="tresc-pomoc" className="sr-only">
        Możesz wkleić kilka zdań naraz: rozdzielimy je na osobne twierdzenia. Ctrl+Enter wysyła.
      </p>
      {error && (
        <p role="alert" className="text-body-sm text-warning">
          {error}
        </p>
      )}
    </form>
  )
}
