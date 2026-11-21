import { Link, Outlet } from '@tanstack/react-router'

import { LogoMark } from './LogoMark'

const NAV_ITEMS = [
  { to: '/', label: 'Sprawdź' },
  { to: '/historia', label: 'Historia' },
  { to: '/zrodla', label: 'Źródła' },
  { to: '/jak-to-dziala', label: 'Jak to działa' },
] as const
const DISCORD_INVITE_URL =
  'https://discord.com/oauth2/authorize?client_id=1573671960204943420&scope=bot%20applications.commands&permissions=84992'
const NAV_LINK_CLASS =
  'relative inline-flex min-h-14 items-center px-3 text-body-sm font-medium transition-colors after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:rounded-full after:transition-colors'

function Wordmark() {
  return (
    <Link to="/" className="flex items-center gap-2 rounded-md" aria-label="Prawdowid, strona główna">
      <LogoMark className="size-7" />
      <span className="text-heading font-bold tracking-tight text-ink">Prawdowid</span>
    </Link>
  )
}

/** Full-height app shell: a slim header and one centred column, like a chat app. */
export function Layout() {
  return (
    <div className="flex min-h-dvh flex-col overflow-x-clip">
      <a
        href="#tresc"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-20 focus:rounded-md focus:bg-surface focus:px-4 focus:py-2"
      >
        Przejdź do treści
      </a>
      <header className="sticky top-0 z-10 border-b border-border bg-surface/95 backdrop-blur">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-x-6 px-4">
          <Wordmark />
          <nav aria-label="Główna nawigacja">
            <ul className="flex flex-wrap">
              {NAV_ITEMS.map((item) => (
                <li key={item.to}>
                  <Link
                    to={item.to}
                    activeOptions={{ exact: item.to === '/' }}
                    activeProps={{
                      className: `${NAV_LINK_CLASS} font-semibold text-ink after:bg-brand-600`,
                      'aria-current': 'page',
                    }}
                    inactiveProps={{
                      className: `${NAV_LINK_CLASS} text-ink-muted after:bg-transparent hover:text-ink hover:after:bg-border-control`,
                    }}
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
              <li>
                <a
                  href={DISCORD_INVITE_URL}
                  target="_blank"
                  rel="noreferrer"
                  className={`${NAV_LINK_CLASS} text-ink-muted after:bg-transparent hover:text-ink hover:after:bg-border-control`}
                >
                  Bot Discord
                  <span className="sr-only"> (otwiera się w nowej karcie)</span>
                </a>
              </li>
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
