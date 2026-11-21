import { createFileRoute } from '@tanstack/react-router'

import { RouteError, RouteLoading } from '../components/RouteStates'
import { ResultPage } from '../pages/ResultPage'
import { getResult } from '../lib/resultCache'

export const Route = createFileRoute('/wynik/$checkId')({
  loader: ({ params }) => getResult(params.checkId),
  component: function ResultRoute() {
    return <ResultPage cached={Route.useLoaderData()} />
  },
  pendingComponent: () => <RouteLoading text="Wczytujemy wynik…" />,
  errorComponent: RouteError,
})
