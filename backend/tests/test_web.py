"""Tests for src/sources/web.py. They read a saved HTML file, so no internet needed."""

from pathlib import Path

from src.sources import web

SAMPLE = Path(__file__).parent.parent / "data" / "sample_hackathon.html"
BASE = "https://example.com/events/mfu-hackathon"


def test_html_to_text_keeps_content_and_drops_noise():
    title, text, _ = web.html_to_text(SAMPLE.read_text(encoding="utf-8"), BASE)

    assert title == "MFU Hackathon 2027"
    assert "ปิดรับสมัคร: 31 มกราคม 2570" in text  # Thai text survives
    assert "tracking code" not in text  # <script> removed
    assert "font-family" not in text  # <style> removed
    assert "Example Org" not in text  # <footer> removed
    assert "\n\n" not in text  # empty lines collapsed


def test_html_to_text_makes_links_absolute():
    _, _, links = web.html_to_text(SAMPLE.read_text(encoding="utf-8"), BASE)

    assert "https://example.com/register" in links
    # links inside <nav> are still collected (register buttons can live there)
    assert "https://example.com/about" in links


def test_fetch_url_refuses_when_robots_disallows(monkeypatch):
    monkeypatch.setattr(web, "is_allowed_by_robots", lambda url, ua: False)
    try:
        web.fetch_url(BASE)
        assert False, "should have raised FetchError"
    except web.FetchError as e:
        assert "robots.txt" in str(e)


# ---------------------------------------------------------------------------
# Main content, robots.txt edge cases, following links
# ---------------------------------------------------------------------------
from types import SimpleNamespace

from src.models import RawDocument

NEWS = Path(__file__).parent.parent / "data" / "sample_news_detail.html"


def test_html_to_text_reads_only_main_when_present():
    title, text, links = web.html_to_text(NEWS.read_text(encoding="utf-8"), "https://uni.example/news/1.html")

    assert "Workshop Git" in title
    assert "รับสมัครถึง 1 ธันวาคม 2569" in text
    assert "มาตรการส่งเสริมความโปร่งใส" not in text  # menu outside <main> is gone
    assert links == ["https://forms.example.com/git-workshop"]  # menu links are gone too


def fake_response(url, status=200, content_type="text/plain", text=""):
    return SimpleNamespace(url=url, status_code=status, headers={"content-type": content_type}, text=text)


def test_robots_redirected_to_html_means_no_rules(monkeypatch):
    web._robots_cache.clear()
    # like mfu.ac.th: /robots.txt redirects to an HTML landing page
    monkeypatch.setattr(web.requests, "get", lambda *a, **k: fake_response(
        "https://uni.example/landing.html", content_type="text/html", text="<html>Disallow: /</html>"))

    assert web.is_allowed_by_robots("https://uni.example/news/1.html", "Bot") is True


def test_robots_disallow_is_respected(monkeypatch):
    web._robots_cache.clear()
    monkeypatch.setattr(web.requests, "get", lambda *a, **k: fake_response(
        "https://uni.example/robots.txt", text="User-agent: *\nDisallow: /private/"))

    assert web.is_allowed_by_robots("https://uni.example/private/x.html", "Bot") is False
    assert web.is_allowed_by_robots("https://uni.example/news/1.html", "Bot") is True


def test_find_detail_links_filters_and_limits():
    listing = RawDocument(source_type="web", source_ref="https://uni.example/news.html", text="x", links=[
        "https://uni.example/about.html",
        "https://uni.example/news/news-detail/1.html",
        "https://uni.example/news/news-detail/2.html",
        "https://uni.example/news/news-detail/3.html",
    ])

    assert web.find_detail_links(listing, "news-detail", limit=2) == [
        "https://uni.example/news/news-detail/1.html",
        "https://uni.example/news/news-detail/2.html",
    ]
