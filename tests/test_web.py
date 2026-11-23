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
