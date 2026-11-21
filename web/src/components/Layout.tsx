import { Link, Outlet } from '@tanstack/react-router'

import { setLocale, useLocale, useMessages } from '../lib/i18n'
import type { Locale } from '../lib/i18n'
import { LogoMark } from './LogoMark'

const NAV_ITEMS = [
  { to: '/', key: 'check' },
  { to: '/historia', key: 'history' },
  { to: '/zrodla', key: 'sources' },
  { to: '/jak-to-dziala', key: 'method' },
  { to: '/discord', key: 'discord' },
] as const
const LOCALES: Locale[] = ['pl', 'en']
const NAV_LINK_CLASS =
  'relative inline-flex min-h-14 items-center px-3 text-body-sm font-medium transition-colors after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:rounded-full after:transition-colors'

function Wordmark() {
  const { layout } = useMessages()
  return (
    <Link to="/" className="flex items-center gap-2 rounded-md" aria-label={layout.home}>
      <LogoMark className="size-7" />
      <span className="text-heading font-bold tracking-tight text-ink">Prawdowid</span>
    </Link>
  )
}

function LocaleSwitcher() {
  const locale = useLocale()
  const { layout } = useMessages()
  return (
    <fieldset className="flex rounded-md border border-border p-0.5">
      <legend className="sr-only">{layout.language}</legend>
      {LOCALES.map((option) => (
        <button
          key={option}
          type="button"
          lang={option}
          aria-pressed={locale === option}
          onClick={() => setLocale(option)}
          className={`min-h-9 rounded-sm px-2.5 font-mono text-meta uppercase transition-colors ${
            locale === option ? 'bg-ink text-ink-inverse' : 'text-ink-muted hover:text-ink'
          }`}
        >
          {option}
        </button>
      ))}
    </fieldset>
  )
}

/** Full-height app shell: a slim header and one centred column, like a chat app. */
export function Layout() {
  const { layout } = useMessages()
  return (
    <div className="flex min-h-dvh flex-col overflow-x-clip">
      <a
        href="#tresc"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-20 focus:rounded-md focus:bg-surface focus:px-4 focus:py-2"
      >
        {layout.skipToContent}
      </a>
      <header className="sticky top-0 z-10 border-b border-border bg-surface/95 backdrop-blur">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-x-6 px-4">
          <Wordmark />
          <nav aria-label={layout.mainNav} className="flex items-center gap-3">
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
                    {layout.nav[item.key]}
                  </Link>
                </li>
              ))}
            </ul>
            <LocaleSwitcher />
          </nav>
        </div>
      </header>
      <main id="tresc" className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4">
        <Outlet />
      </main>
    </div>
  )
}
