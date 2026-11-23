"""Web source: URL -> RawDocument.

Polite scraping rules (from the brief):
- respect robots.txt
- send a User-Agent that says who we are
- wait between requests to the same site
- never log in to a site
"""

import os
import re
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from src.models import RawDocument

DEFAULT_USER_AGENT = "EventScoutBot/0.1 (student project)"
TIMEOUT_SECONDS = 20
MAX_LINKS = 150  # enough to find a register link, without wasting tokens
MAX_TEXT_CHARS = 100_000  # safety cap; we warn instead of cutting silently
MIN_TEXT_CHARS = 300  # less than this usually means the page is built by JavaScript
DELAY_BETWEEN_REQUESTS = 1.0  # seconds; be gentle with university servers

# Tags that never contain event info, only noise.
NOISE_TAGS = ["script", "style", "noscript", "svg", "iframe", "nav", "footer", "form"]

# Where the "real" content usually lives. We try these in order.
MAIN_CONTENT_SELECTORS = ["main", "[role=main]", "article"]

# robots.txt answers are cached per site, so following 10 links = 1 robots.txt request.
_robots_cache: dict[str, RobotFileParser | None] = {}


class FetchError(Exception):
    """Raised when we can't (or shouldn't) fetch a page."""


def _user_agent() -> str:
    return os.getenv("SCRAPER_USER_AGENT") or DEFAULT_USER_AGENT


def _load_robots(site: str, user_agent: str) -> RobotFileParser | None:
    """Download and parse robots.txt for one site. None means "no rules"."""
    try:
        resp = requests.get(f"{site}/robots.txt", headers={"User-Agent": user_agent}, timeout=TIMEOUT_SECONDS)
    except requests.RequestException:
        return None
    if resp.status_code >= 400:
        return None  # no robots.txt -> no rules

    # Some sites (e.g. mfu.ac.th) redirect /robots.txt to their HTML home page.
    # That is not a robots file, so we must not try to read HTML as rules.
    content_type = resp.headers.get("content-type", "")
    if not resp.url.endswith("/robots.txt") or "text/plain" not in content_type:
        return None

    parser = RobotFileParser()
    parser.parse(resp.text.splitlines())
    return parser


def is_allowed_by_robots(url: str, user_agent: str) -> bool:
    """True if robots.txt allows this URL (or the site has no real robots.txt)."""
    parsed = urlparse(url)
    site = f"{parsed.scheme}://{parsed.netloc}"
    if site not in _robots_cache:
        _robots_cache[site] = _load_robots(site, user_agent)
    parser = _robots_cache[site]
    return True if parser is None else parser.can_fetch(user_agent, url)


def _main_content(soup: BeautifulSoup):
    """Return the part of the page that holds the article, or the whole body.

    University sites repeat a huge menu on every page. Reading only <main>
    removes it, which saves tokens and stops the LLM from getting confused.
    """
    for selector in MAIN_CONTENT_SELECTORS:
        element = soup.select_one(selector)
        if element is not None and element.get_text(strip=True):
            return element
    return soup.body or soup


def html_to_text(html: str, base_url: str) -> tuple[str | None, str, list[str]]:
    """Turn raw HTML into (title, clean_text, links).

    Kept separate from fetching so we can unit-test it with saved HTML files
    without touching the internet.
    """
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else None
    content = _main_content(soup)

    # Collect links BEFORE removing tags (register buttons are often inside <form>/<nav>).
    links: list[str] = []
    for a in content.find_all("a", href=True):
        href = urljoin(base_url, a["href"])  # make relative links absolute
        if href.startswith("http") and href not in links:
            links.append(href)
        if len(links) >= MAX_LINKS:
            break

    for tag in content(NOISE_TAGS):
        tag.decompose()

    # "\n" as separator keeps paragraphs apart; then drop empty lines.
    raw_text = content.get_text("\n")
    lines = [line.strip() for line in raw_text.splitlines()]
    text = "\n".join(line for line in lines if line)
    return title, text, links


def fetch_url(url: str) -> RawDocument:
    """Download one page and return it as a RawDocument."""
    user_agent = _user_agent()

    if not is_allowed_by_robots(url, user_agent):
        raise FetchError(f"robots.txt does not allow fetching {url}")

    try:
        resp = requests.get(url, headers={"User-Agent": user_agent}, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise FetchError(f"Could not fetch {url}: {e}") from e

    # Many Thai sites don't declare their encoding; requests then falls back to
    # ISO-8859-1 and Thai text turns into garbage. Let it detect the real one.
    if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding

    title, text, links = html_to_text(resp.text, base_url=resp.url)

    if not text:
        raise FetchError(
            f"No text found at {url}. The page may need JavaScript (Playwright, later phase)."
        )
    if len(text) < MIN_TEXT_CHARS:
        print(
            f"[warn] Only {len(text)} chars of text. This page probably needs JavaScript "
            "(Playwright, later phase), so results may be empty."
        )
    if len(text) > MAX_TEXT_CHARS:
        print(f"[warn] Page text is {len(text):,} chars; only the first {MAX_TEXT_CHARS:,} are used.")
        text = text[:MAX_TEXT_CHARS]

    return RawDocument(source_type="web", source_ref=url, title=title, text=text, links=links)


def find_detail_links(listing: RawDocument, pattern: str, limit: int) -> list[str]:
    """Pick the links on a listing page that point to detail pages.

    `pattern` is a regular expression, e.g. "news-detail" for mfu.ac.th.
    We use a pattern per site because every site builds its URLs differently,
    and a simple rule we can read is easier to debug than a clever guess.
    """
    regex = re.compile(pattern)
    matches = [link for link in listing.links if regex.search(link)]
    return matches[:limit]


def fetch_listing(url: str, follow_pattern: str, max_items: int = 5) -> list[RawDocument]:
    """Fetch a listing page, then each detail page it links to.

    Returns the detail pages only. A detail page that fails is skipped with a
    warning, so one broken link doesn't stop the whole run.
    """
    listing = fetch_url(url)
    detail_urls = find_detail_links(listing, follow_pattern, max_items)
    if not detail_urls:
        print(f"[warn] No links matching '{follow_pattern}' on {url}")

    documents: list[RawDocument] = []
    for detail_url in detail_urls:
        time.sleep(DELAY_BETWEEN_REQUESTS)
        try:
            documents.append(fetch_url(detail_url))
        except FetchError as e:
            print(f"[warn] Skipped {detail_url}: {e}")
    return documents
