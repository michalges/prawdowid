type ElementOptions = {
  className?: string
  text?: string
  attributes?: Record<string, string>
}

/** Builds DOM without innerHTML: results contain third-party quotes. */
export function createElement<Tag extends keyof HTMLElementTagNameMap>(
  tag: Tag,
  options: ElementOptions = {},
  children: (Node | null)[] = [],
): HTMLElementTagNameMap[Tag] {
  const element = document.createElement(tag)
  if (options.className) element.className = options.className
  if (options.text !== undefined) element.textContent = options.text
  for (const [name, value] of Object.entries(options.attributes ?? {})) element.setAttribute(name, value)
  for (const child of children) if (child) element.append(child)
  return element
}

export function createExternalLink(
  href: string,
  text: string,
  className?: string,
): HTMLAnchorElement | HTMLSpanElement {
  if (!/^https?:\/\//i.test(href)) return createElement('span', { className, text })
  return createElement('a', { className, text, attributes: { href, target: '_blank', rel: 'noopener noreferrer' } })
}

export function getRequiredElement<Type extends HTMLElement>(id: string, type: new () => Type): Type {
  const element = document.getElementById(id)
  if (!(element instanceof type)) throw new Error(`Missing #${id}`)
  return element
}
