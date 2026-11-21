import { createRootRoute, Link } from '@tanstack/react-router'

import { Layout } from '../components/Layout'

function NotFoundPage() {
  return (
    <div className="flex flex-col gap-3">
      <h1 className="text-title font-semibold text-ink">Nie ma takiej strony</h1>
      <Link to="/" className="w-fit font-medium text-brand-700 underline underline-offset-2">
        Wróć do sprawdzania
      </Link>
    </div>
  )
}

export const Route = createRootRoute({
  component: Layout,
  notFoundComponent: NotFoundPage,
})
