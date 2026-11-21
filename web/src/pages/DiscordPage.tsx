import { ExternalLink } from 'lucide-react'

import { useMessages } from '../lib/i18n'

const DISCORD_CLIENT_ID = '1573671960204943420'
const DISCORD_BOT_PERMISSIONS = '84992'

const USER_INSTALL_URL = `https://discord.com/oauth2/authorize?client_id=${DISCORD_CLIENT_ID}&integration_type=1&scope=applications.commands`
const GUILD_INSTALL_URL = `https://discord.com/oauth2/authorize?client_id=${DISCORD_CLIENT_ID}&integration_type=0&scope=bot%20applications.commands&permissions=${DISCORD_BOT_PERMISSIONS}`

export function DiscordPage() {
  const { discord } = useMessages()
  const installOptions = [
    { title: discord.userInstallTitle, description: discord.userInstallText, href: USER_INSTALL_URL },
    { title: discord.guildInstallTitle, description: discord.guildInstallText, href: GUILD_INSTALL_URL },
  ]
  return (
    <div className="divide-y divide-border py-2">
      <header className="flex flex-col gap-3 py-8 sm:py-10">
        <h1 className="text-title font-semibold text-ink">{discord.title}</h1>
        <p className="text-body text-ink-muted">{discord.intro}</p>
      </header>

      <section className="flex flex-col gap-5 py-8 sm:py-10">
        <h2 className="text-heading font-semibold text-ink">{discord.addTitle}</h2>
        <ul className="flex flex-col gap-3 sm:flex-row">
          {installOptions.map((option) => (
            <li key={option.title} className="flex flex-1">
              <a
                href={option.href}
                target="_blank"
                rel="noopener noreferrer"
                className="flex flex-1 flex-col gap-2 rounded-md border border-border-control p-4 transition-colors hover:border-brand-600"
              >
                <span className="inline-flex items-center gap-1 text-body font-semibold text-ink">
                  {option.title}
                  <ExternalLink aria-hidden className="size-3.5" />
                </span>
                <span className="text-body-sm text-ink-muted">{option.description}</span>
              </a>
            </li>
          ))}
        </ul>
      </section>

      <section className="flex flex-col gap-5 py-8 sm:py-10">
        <h2 className="text-heading font-semibold text-ink">{discord.commandsTitle}</h2>
        <dl className="flex flex-col gap-3">
          {discord.commands.map(([command, description]) => (
            <div key={command} className="flex flex-col gap-1 sm:flex-row sm:gap-4">
              <dt className="font-mono text-body-sm text-ink sm:w-40">{command}</dt>
              <dd className="text-body-sm text-ink-muted">{description}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  )
}
