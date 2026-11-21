import { Link, Outlet } from '@tanstack/react-router'
import { Check, ChevronDown, Languages, Menu, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

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
const LOCALE_LABELS: Record<Locale, string> = { pl: 'Polski', en: 'English' }
const LOCALES: Locale[] = ['pl', 'en']
const SHEET_LINK_CLASS = 'flex min-h-12 items-center rounded-md px-3 text-body font-medium'
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
  const [isOpen, setIsOpen] = useState(false)
  const container = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return
    function closeOnOutsideClick(event: PointerEvent) {
      if (event.target instanceof Node && !container.current?.contains(event.target)) setIsOpen(false)
    }
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setIsOpen(false)
    }
    document.addEventListener('pointerdown', closeOnOutsideClick)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('pointerdown', closeOnOutsideClick)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [isOpen])

  function selectLocale(value: Locale) {
    setLocale(value)
    setIsOpen(false)
  }

  return (
    <div ref={container} className="relative">
      <button
        type="button"
        aria-expanded={isOpen}
        aria-label={`${layout.language}: ${LOCALE_LABELS[locale]}`}
        onClick={() => setIsOpen((wasOpen) => !wasOpen)}
        className="inline-flex min-h-9 items-center gap-1.5 rounded-md border border-border px-2.5 text-body-sm font-medium text-ink hover:border-border-control aria-expanded:border-border-control aria-expanded:bg-surface-subtle"
      >
        <Languages aria-hidden className="size-4 text-ink-muted" />
        <span className="font-mono text-meta uppercase">{locale}</span>
        <ChevronDown aria-hidden className={`size-3.5 text-ink-muted transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      {isOpen && (
        <ul className="absolute right-0 z-20 mt-1.5 w-44 overflow-hidden rounded-lg border border-border bg-surface p-1 shadow-card">
          {LOCALES.map((option) => {
            const isSelected = option === locale
            return (
              <li key={option}>
                <button
                  type="button"
                  lang={option}
                  aria-pressed={isSelected}
                  onClick={() => selectLocale(option)}
                  className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-body-sm ${
                    isSelected ? 'bg-surface-subtle font-semibold text-ink' : 'text-ink-muted hover:bg-surface-subtle hover:text-ink'
                  }`}
                >
                  <span className="w-6 font-mono text-meta uppercase text-ink-subtle">{option}</span>
                  <span className="flex-1">{LOCALE_LABELS[option]}</span>
                  {isSelected && <Check aria-hidden className="size-4 text-brand-600" />}
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

function NavLinks({ variant, onNavigate }: { variant: 'bar' | 'sheet'; onNavigate?: () => void }) {
  const { layout } = useMessages()
  const isBar = variant === 'bar'
  return (
    <ul className={isBar ? 'flex' : 'flex flex-col gap-1'}>
      {NAV_ITEMS.map((item) => (
        <li key={item.to}>
          <Link
            to={item.to}
            onClick={onNavigate}
            activeOptions={{ exact: item.to === '/' }}
            activeProps={{
              className: isBar
                ? `${NAV_LINK_CLASS} font-semibold text-ink after:bg-brand-600`
                : `${SHEET_LINK_CLASS} bg-brand-50 font-semibold text-brand-700`,
              'aria-current': 'page',
            }}
            inactiveProps={{
              className: isBar
                ? `${NAV_LINK_CLASS} text-ink-muted after:bg-transparent hover:text-ink hover:after:bg-border-control`
                : `${SHEET_LINK_CLASS} text-ink hover:bg-surface-subtle`,
            }}
          >
            {layout.nav[item.key]}
          </Link>
        </li>
      ))}
    </ul>
  )
}

/** Below `md` the links move into a side sheet; a native dialog gives focus trapping and Escape. */
function MobileNav() {
  const { layout } = useMessages()
  const dialog = useRef<HTMLDialogElement>(null)

  function closeSheet() {
    dialog.current?.close()
  }

  useEffect(() => {
    const element = dialog.current
    if (!element) return
    function closeOnBackdropClick(event: MouseEvent) {
      if (event.target === element) element?.close()
    }
    element.addEventListener('click', closeOnBackdropClick)
    return () => element.removeEventListener('click', closeOnBackdropClick)
  }, [])

  return (
    <>
      <button
        type="button"
        onClick={() => dialog.current?.showModal()}
        aria-label={layout.openMenu}
        className="inline-flex size-11 items-center justify-center rounded-md text-ink hover:bg-surface-subtle"
      >
        <Menu aria-hidden className="size-5" />
      </button>
      <dialog
        ref={dialog}
        aria-label={layout.mainNav}
        className="fixed inset-y-0 right-0 left-auto m-0 h-dvh max-h-dvh w-[min(20rem,85vw)] max-w-none bg-surface p-0 shadow-card backdrop:bg-ink/40 backdrop:backdrop-blur-sm open:animate-[sheet-in_200ms_ease-out]"
      >
        <div className="flex h-full flex-col gap-6 p-4">
          <div className="flex items-center justify-between">
            <Wordmark />
            <button
              type="button"
              onClick={closeSheet}
              aria-label={layout.closeMenu}
              className="inline-flex size-11 items-center justify-center rounded-md text-ink hover:bg-surface-subtle"
            >
              <X aria-hidden className="size-5" />
            </button>
          </div>
          <nav aria-label={layout.mainNav}>
            <NavLinks variant="sheet" onNavigate={closeSheet} />
          </nav>
        </div>
      </dialog>
    </>
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
        <div className="mx-auto flex min-h-14 max-w-3xl items-center justify-between gap-x-6 px-4">
          <Wordmark />
          <div className="flex items-center gap-2 md:gap-3">
            <nav aria-label={layout.mainNav} className="hidden md:block">
              <NavLinks variant="bar" />
            </nav>
            <LocaleSwitcher />
            <div className="md:hidden">
              <MobileNav />
            </div>
          </div>
        </div>
      </header>
      <main id="tresc" className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4">
        <Outlet />
      </main>
    </div>
  )
}
