import { createRootRoute, Link } from '@tanstack/react-router'

import { Layout } from '../components/Layout'
import { useMessages } from '../lib/i18n'

function NotFoundPage() {
  const { notFound } = useMessages()
  return (
    <div className="flex flex-col gap-3">
      <h1 className="text-title font-semibold text-ink">{notFound.title}</h1>
      <Link to="/" className="w-fit font-medium text-brand-700 underline underline-offset-2">
        {notFound.back}
      </Link>
    </div>
  )
}

export const Route = createRootRoute({
  component: Layout,
  notFoundComponent: NotFoundPage,
})
