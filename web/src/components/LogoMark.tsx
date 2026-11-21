/**
 * "Oko na krzyżu" mark, inlined from docs/design/logo (DESIGN.md §9). Don't recolour.
 * `reversed` is the app-icon artwork without its tile, for use on brand-600.
 */
export function LogoMark({
  className,
  label,
  isReversed = false,
}: {
  className?: string
  label?: string
  isReversed?: boolean
}) {
  const ink = '#16181d'
  const ray = isReversed ? ink : '#d4213d'
  const body = isReversed ? '#ffffff' : ink
  const iris = isReversed ? ink : '#ffffff'
  return (
    <svg
      viewBox="0 0 48 48"
      className={className}
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <path d="M24 11C21.2 8.2 21.2 4.4 24 1.2C26.8 4.4 26.8 8.2 24 11Z" fill={ray} />
      <path d="M24 37C26.8 39.8 26.8 43.6 24 46.8C21.2 43.6 21.2 39.8 24 37Z" fill={body} />
      <path d="M4 24C10.5 9.5 37.5 9.5 44 24C37.5 38.5 10.5 38.5 4 24Z" fill={body} />
      <circle cx="24" cy="24" r={isReversed ? 7.4 : 7.6} fill={iris} />
      <circle cx="24" cy="24" r={isReversed ? 3 : 3.8} fill="#d4213d" />
    </svg>
  )
}
