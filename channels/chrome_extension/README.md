# Prawdowid: Chrome extension

Manifest V3 extension. It is a thin client of `POST /v1/checks` (channel `browser_extension`) with no verification
logic, like the Discord bot.

- **Popup:** paste text or a link, check the current page's URL, or check a screenshot of the visible tab (OCR path).
- **Context menu:** "Sprawdź … w Prawdowidzie" on selected text, a link, or the page.
- Results show verdict, explanation, up to 3 quotes with source links, and a link to the full result on the web
  (`/wynik/{id}`).
- Checks run in the service worker, so closing the popup doesn't cancel them. A badge marks a finished result.
- **Options:** server address (default `http://localhost:8080`, the web app, whose nginx proxies `/v1`) and
  "Usuń moje dane" (`DELETE /v1/sessions/{id}`). Session ids are random per install (`ext-…`).

## Build & load

```bash
pnpm install
pnpm build        # → dist/
pnpm package      # → prawdowid-extension.zip (Chrome Web Store upload)
```

Chrome → `chrome://extensions` → Developer mode → "Load unpacked" → `dist/`.

Saving a non-localhost server asks for host permission on that origin only (`optional_host_permissions`).
Icons are exported from `docs/design/logo/prawdowid-app-icon.svg`.
