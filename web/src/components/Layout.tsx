import { Link, Outlet } from '@tanstack/react-router'

const NAV_ITEMS = [
  { to: '/', label: 'Sprawdź' },
  { to: '/historia', label: 'Historia' },
  { to: '/zrodla', label: 'Źródła' },
  { to: '/jak-to-dziala', label: 'Jak to działa' },
] as const
const NAV_LINK_CLASS = 'inline-flex min-h-11 items-center rounded-pill px-3 text-body-sm font-medium'

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

/** Full-height app shell: a slim header and one centred column, like a chat app. */
export function Layout() {
  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#tresc"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-20 focus:rounded-md focus:bg-surface focus:px-4 focus:py-2"
      >
        Przejdź do treści
      </a>
      <header className="sticky top-0 z-10 border-b border-border bg-surface/95 backdrop-blur">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-x-6 gap-y-1 px-4 py-2">
          <Wordmark />
          <nav aria-label="Główna nawigacja">
            <ul className="flex flex-wrap gap-0.5">
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
      <main id="tresc" className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4">
        <Outlet />
      </main>
    </div>
  )
}
