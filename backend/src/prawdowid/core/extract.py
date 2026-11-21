"""Main-text and metadata extraction from HTML (trafilatura)."""

from dataclasses import dataclass
from datetime import date
from urllib.parse import urldefrag, urljoin, urlsplit

import lxml.html
import trafilatura

from prawdowid.core.text import normalize_whitespace

MIN_ARTICLE_CHARS = 200
PUBLICATION_FOOTER_MARKERS = (
    "Informacje o publikacji dokumentu",
    "Metryczka",
    "Pierwsza publikacja:",
)


def get_text_without_footer(text: str) -> str:
    """Drops CMS publication footers (they list staff names and add no facts)."""
    cut = min(
        (text.find(marker) for marker in PUBLICATION_FOOTER_MARKERS if marker in text), default=-1
    )
    return text[:cut].rstrip(" -\n") if cut > 0 else text


@dataclass(frozen=True)
class ExtractedArticle:
    title: str
    text: str
    published_at: date | None


def get_parsed_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def extract_article(html: str, url: str) -> ExtractedArticle | None:
    extracted = trafilatura.bare_extraction(
        html,
        url=url,
        with_metadata=True,
        include_comments=False,
        include_tables=False,
        favor_precision=True,
    )
    if extracted is None:
        return None
    fields = extracted if isinstance(extracted, dict) else extracted.as_dict()
    text = get_text_without_footer((fields.get("text") or "").strip())
    if len(text) < MIN_ARTICLE_CHARS:
        return None
    title = normalize_whitespace(fields.get("title") or "") or url
    return ExtractedArticle(
        title=title, text=text, published_at=get_parsed_date(fields.get("date"))
    )


NAVIGATION_TAGS = frozenset({"nav", "header", "footer", "aside"})
NAVIGATION_HINTS = ("menu", "nav", "breadcrumb", "footer", "header", "sidebar", "cookie")
MIN_ARTICLE_LINK_WORDS = 5


def is_in_navigation(element: lxml.html.HtmlElement) -> bool:
    for ancestor in element.iterancestors():
        if ancestor.tag in NAVIGATION_TAGS:
            return True
        marker = f"{ancestor.get('class', '')} {ancestor.get('id', '')} {ancestor.get('role', '')}"
        if any(hint in marker.lower() for hint in NAVIGATION_HINTS):
            return True
    return False


def get_article_links(html: str, base_url: str, path_prefix: str | None = None) -> list[str]:
    """Same-site links that look like article teasers: outside menus, with a sentence-like title."""
    try:
        tree = lxml.html.fromstring(html)
    except (lxml.etree.ParserError, ValueError):
        return []
    allowed = set(get_same_site_links(html, base_url, path_prefix))
    links: dict[str, None] = {}
    for element in tree.iter("a"):
        absolute_url, _fragment = urldefrag(urljoin(base_url, element.get("href") or ""))
        if absolute_url not in allowed or is_in_navigation(element):
            continue
        title = normalize_whitespace(element.text_content() or element.get("title") or "")
        if len(title.split()) >= MIN_ARTICLE_LINK_WORDS:
            links[absolute_url] = None
    return list(links)


def get_same_site_links(html: str, base_url: str, path_prefix: str | None = None) -> list[str]:
    """Absolute links on the same host, optionally under a path prefix, in page order."""
    try:
        tree = lxml.html.fromstring(html)
    except (lxml.etree.ParserError, ValueError):
        return []
    base_host = urlsplit(base_url).netloc
    links: dict[str, None] = {}
    for element in tree.iter("a"):
        href = element.get("href")
        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        absolute_url, _fragment = urldefrag(urljoin(base_url, href))
        parts = urlsplit(absolute_url)
        if parts.netloc != base_host or parts.scheme not in ("http", "https"):
            continue
        if path_prefix and not parts.path.startswith(path_prefix):
            continue
        links[absolute_url] = None
    return list(links)
