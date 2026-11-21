import { createFileRoute } from '@tanstack/react-router'

import { DiscordPage } from '../pages/DiscordPage'

export const Route = createFileRoute('/discord')({ component: DiscordPage })
