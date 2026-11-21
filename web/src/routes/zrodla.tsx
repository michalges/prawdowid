import { createFileRoute } from '@tanstack/react-router'

import { getSources } from '../api/client'
import { RouteError, RouteLoading } from '../components/RouteStates'
import { SourcesPage } from '../pages/SourcesPage'

export const Route = createFileRoute('/zrodla')({
  loader: () => getSources(),
  component: function SourcesRoute() {
    return <SourcesPage catalog={Route.useLoaderData()} />
  },
  pendingComponent: () => <RouteLoading text="Wczytujemy katalog…" />,
  errorComponent: RouteError,
})
