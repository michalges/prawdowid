import { Link } from '@tanstack/react-router'
import { ArrowRight } from 'lucide-react'

import type { Verdict } from '../api/types'
import { TransparencyNote } from '../components/TransparencyNote'
import { VerdictBadge } from '../components/VerdictBadge'
import { useMessages } from '../lib/i18n'
import { VERDICT_STYLES } from '../lib/verdicts'

export function MethodPage() {
  const { method, verdicts } = useMessages()
  return (
    <div className="divide-y divide-border py-2">
      <header className="flex flex-col gap-3 py-8 sm:py-10">
        <h1 className="text-title font-semibold text-ink">{method.title}</h1>
        <p className="text-body text-ink-muted">{method.intro}</p>
      </header>

      <section className="flex flex-col gap-5 py-8 sm:py-10">
        <h2 className="text-heading font-semibold text-ink">{method.stepsTitle}</h2>
        <ol className="flex flex-col gap-4">
          {method.steps.map(([title, text], index) => (
            <li key={title} className="flex gap-4">
              <span className="flex size-8 shrink-0 items-center justify-center rounded-pill bg-surface-subtle font-mono text-body-sm text-ink">
                {index + 1}
              </span>
              <div>
                <h3 className="text-body font-semibold text-ink">{title}</h3>
                <p className="text-body-sm text-ink-muted">{text}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="flex flex-col gap-5 py-8 sm:py-10">
        <h2 className="text-heading font-semibold text-ink">{method.verdictsTitle}</h2>
        <ul className="flex flex-col gap-3">
          {(Object.keys(VERDICT_STYLES) as Verdict[]).map((verdict) => (
            <li key={verdict} className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
              <span className="sm:w-72">
                <VerdictBadge verdict={verdict} />
              </span>
              <span className="text-body-sm text-ink-muted">{verdicts[verdict].description}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="flex flex-col gap-4 py-8 sm:py-10">
        <h2 className="text-heading font-semibold text-ink">{method.strengthTitle}</h2>
        <p className="text-body text-ink-muted">{method.strengthText}</p>
      </section>

      <section className="flex flex-col gap-4 py-8 sm:py-10">
        <h2 className="text-heading font-semibold text-ink">{method.notDoTitle}</h2>
        <ul className="flex list-disc flex-col gap-1 pl-5 text-body text-ink-muted">
          {method.notDo.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <TransparencyNote isDetailed />
        <Link
          to="/zrodla"
          className="inline-flex min-h-11 w-fit items-center gap-2 rounded-md bg-ink px-6 text-body font-semibold text-ink-inverse hover:bg-ink/85 active:bg-ink/75"
        >
          {method.seeCatalog}
          <ArrowRight aria-hidden="true" className="size-4" />
        </Link>
      </section>
    </div>
  )
}
