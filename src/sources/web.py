"""Web source: URL -> RawDocument.

Polite scraping rules (from the brief):
- respect robots.txt
- send a User-Agent that says who we are
- never log in to a site
"""

import os
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

# Tags that never contain event info, only noise.
NOISE_TAGS = ["script", "style", "noscript", "svg", "iframe", "nav", "footer", "form"]


class FetchError(Exception):
    """Raised when we can't (or shouldn't) fetch a page."""


def _user_agent() -> str:
    return os.getenv("SCRAPER_USER_AGENT") or DEFAULT_USER_AGENT


def is_allowed_by_robots(url: str, user_agent: str) -> bool:
    """Check the site's robots.txt. If robots.txt can't be read, assume allowed
    (that is the common convention, and what most crawlers do)."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        resp = requests.get(robots_url, headers={"User-Agent": user_agent}, timeout=TIMEOUT_SECONDS)
    except requests.RequestException:
        return True
    if resp.status_code >= 400:
        return True  # no robots.txt -> no rules
    parser = RobotFileParser()
    parser.parse(resp.text.splitlines())
    return parser.can_fetch(user_agent, url)


def html_to_text(html: str, base_url: str) -> tuple[str | None, str, list[str]]:
    """Turn raw HTML into (title, clean_text, links).

    Kept separate from fetching so we can unit-test it with saved HTML files
    without touching the internet.
    """
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else None

    # Collect links BEFORE removing tags (register buttons are often inside <form>/<nav>).
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])  # make relative links absolute
        if href.startswith("http") and href not in links:
            links.append(href)
        if len(links) >= MAX_LINKS:
            break

    for tag in soup(NOISE_TAGS):
        tag.decompose()

    # "\n" as separator keeps paragraphs apart; then drop empty lines.
    raw_text = soup.get_text("\n")
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
