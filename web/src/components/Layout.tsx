import { Link, Outlet } from '@tanstack/react-router'

import { getHealth } from '../api/client'
import { useApi } from '../lib/useApi'

const NAV_ITEMS = [
  { to: '/', label: 'Sprawdź' },
  { to: '/historia', label: 'Historia' },
  { to: '/zrodla', label: 'Źródła' },
  { to: '/jak-to-dziala', label: 'Jak to działa' },
] as const
const NAV_LINK_CLASS = 'inline-flex min-h-11 items-center rounded-md px-3 text-body-sm font-medium'

function Wordmark() {
  return (
    <Link to="/" className="flex items-center gap-2 rounded-md" aria-label="Prawdowid, strona główna">
      <span aria-hidden className="flex h-4 w-6 flex-col overflow-hidden rounded-sm border border-border">
        <span className="flex-1 bg-surface" />
        <span className="flex-1 bg-brand-600" />
      </span>
      <span className="text-heading font-bold tracking-tight text-ink">Prawdowid</span>
    </Link>
  )
}

function TransparencyFooter() {
  const health = useApi('health', getHealth)
  return (
    <footer className="mt-16 border-t border-border bg-surface-subtle">
      <div className="mx-auto flex max-w-5xl flex-col gap-3 px-4 py-8 text-body-sm text-ink-muted sm:px-6">
        <p>Prawdowid wspiera ocenę informacji. Nie jest „sędzią prawdy”. Zawsze zajrzyj do źródeł.</p>
        {health.status === 'ready' && (
          <>
            <p>{health.data.data_processing_pl}</p>
            <p className="font-mono text-meta text-ink-subtle">
              model: {health.data.llm_provider} · korpus: {health.data.corpus_version ?? 'brak'} · OCR:{' '}
              {health.data.ocr} · wersja {health.data.version}
            </p>
          </>
        )}
        <Link to="/historia" className="w-fit font-medium text-brand-700 underline underline-offset-2">
          Usuń moje dane
        </Link>
      </div>
    </footer>
  )
}

export function Layout() {
  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#tresc"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-10 focus:rounded-md focus:bg-surface focus:px-4 focus:py-2"
      >
        Przejdź do treści
      </a>
      <header className="border-b border-border">
        <div className="h-1 bg-brand-600" />
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-8 gap-y-2 px-4 py-3 sm:px-6">
          <Wordmark />
          <nav aria-label="Główna nawigacja">
            <ul className="flex flex-wrap gap-1">
              {NAV_ITEMS.map((item) => (
                <li key={item.to}>
                  <Link
                    to={item.to}
                    activeOptions={{ exact: item.to === '/' }}
                    activeProps={{ className: `${NAV_LINK_CLASS} bg-brand-50 text-brand-800`, 'aria-current': 'page' }}
                    inactiveProps={{
                      className: `${NAV_LINK_CLASS} text-ink-muted hover:bg-surface-subtle hover:text-ink`,
                    }}
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </header>
      <main id="tresc" className="mx-auto w-full max-w-5xl flex-1 px-4 pt-8 sm:px-6 sm:pt-12">
        <Outlet />
      </main>
      <TransparencyFooter />
    </div>
  )
}
