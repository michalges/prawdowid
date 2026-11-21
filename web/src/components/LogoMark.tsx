/** "Oko na krzyżu" mark, inlined from docs/design/logo/prawdowid-mark.svg (DESIGN.md §9). Don't recolour. */
export function LogoMark({ className, label }: { className?: string; label?: string }) {
  return (
    <svg
      viewBox="0 0 48 48"
      className={className}
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <path d="M24 11C21.2 8.2 21.2 4.4 24 1.2C26.8 4.4 26.8 8.2 24 11Z" fill="#d4213d" />
      <path d="M24 37C26.8 39.8 26.8 43.6 24 46.8C21.2 43.6 21.2 39.8 24 37Z" fill="#16181d" />
      <path d="M4 24C10.5 9.5 37.5 9.5 44 24C37.5 38.5 10.5 38.5 4 24Z" fill="#16181d" />
      <circle cx="24" cy="24" r="7.6" fill="#ffffff" />
      <circle cx="24" cy="24" r="3.8" fill="#d4213d" />
    </svg>
  )
}
