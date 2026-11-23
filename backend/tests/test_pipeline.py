"""Tests for src/pipeline.py with a fake website and a fake Claude.

The main thing we prove: a page that didn't change is NOT sent to the LLM.
"""

from datetime import date

import pytest
from sqlalchemy import select

from src.db import AgentAction, EventRow, User, WatchedUrl, make_session_factory
from src.extract import ExtractError, ExtractOutput
from src.models import Eligibility, Event, FieldConfidence, RawDocument
from src.pipeline import run_pipeline
from src.sources.web import FetchError

LISTING = "https://uni.example/news.html"
TODAY = date(2026, 11, 23)


class FakeWeb:
    """A tiny pretend website we can edit between runs."""

    def __init__(self):
        self.pages = {
            LISTING: ("ข่าวกิจกรรม", ["https://uni.example/detail/1", "https://uni.example/detail/2"]),
            "https://uni.example/detail/1": ("Workshop Git", []),
            "https://uni.example/detail/2": ("หลักสูตรพยาบาล", []),
        }
        self.body = {url: f"เนื้อหาของ {url}" for url in self.pages}

    def fetch(self, url: str) -> RawDocument:
        if url not in self.pages:
            raise FetchError(f"404 {url}")
        title, links = self.pages[url]
        return RawDocument(source_type="web", source_ref=url, title=title, text=self.body[url], links=links)


class FakeClaude:
    """Returns one event per page and counts how often it was asked."""

    def __init__(self):
        self.calls: list[str] = []
        self.fail_on: set[str] = set()

    def extract(self, doc: RawDocument) -> ExtractOutput:
        self.calls.append(doc.source_ref)
        if doc.source_ref in self.fail_on:
            raise ExtractError("pretend failure")
        nurses_only = "detail/2" in doc.source_ref
        event = Event(
            name=doc.title, category="workshop", registration_deadline=date(2026, 12, 1),
            eligibility=Eligibility(allowed_levels=["working"] if nurses_only else None),
            confidence=FieldConfidence(registration_deadline=1, event_dates=1, eligibility=0.9),
            source_ref=doc.source_ref,
        )
        return ExtractOutput(events=[event], input_tokens=100, output_tokens=20)


@pytest.fixture
def setup(tmp_path):
    Session = make_session_factory(f"sqlite:///{tmp_path / 'test.db'}")
    with Session() as db:
        db.add(User(id=1, level="undergraduate"))
        db.add(WatchedUrl(user_id=1, url=LISTING, follow_pattern="detail", max_items=5))
        db.commit()
    return Session, FakeWeb(), FakeClaude()


def run(Session, web, claude):
    with Session() as db:
        return run_pipeline(db, fetch=web.fetch, extract=claude.extract, today=TODAY, delay=0)


def kinds(Session) -> list[str]:
    with Session() as db:
        return [a.kind for a in db.scalars(select(AgentAction).order_by(AgentAction.id))]


def test_first_run_reads_everything_and_logs_it(setup):
    Session, web, claude = setup
    summary = run(Session, web, claude)

    assert summary.llm_calls == 2
    assert summary.events_saved == 2
    assert kinds(Session) == ["read_source", "extract", "extract", "filter_out"]
    with Session() as db:
        reason = db.scalar(select(AgentAction.reason).where(AgentAction.kind == "filter_out"))
    assert "หลักสูตรพยาบาล" in reason  # the nurses-only course was filtered, with a reason


def test_second_run_skips_the_llm_when_nothing_changed(setup):
    Session, web, claude = setup
    run(Session, web, claude)
    claude.calls.clear()

    summary = run(Session, web, claude)

    assert claude.calls == []  # <- the Phase 2 goal
    assert summary.llm_calls == 0
    assert summary.pages_skipped == 1  # the listing itself didn't change, so details weren't even fetched
    assert kinds(Session)[-1] == "skip_unchanged"


def test_new_link_on_listing_reads_only_the_new_page(setup):
    Session, web, claude = setup
    run(Session, web, claude)
    claude.calls.clear()
    web.pages[LISTING] = ("ข่าวกิจกรรม", ["https://uni.example/detail/1", "https://uni.example/detail/2",
                                         "https://uni.example/detail/3"])
    web.pages["https://uni.example/detail/3"] = ("ค่ายอาสา", [])
    web.body["https://uni.example/detail/3"] = "ค่ายอาสา เปิดรับสมัคร"
    web.body[LISTING] = "listing changed"

    summary = run(Session, web, claude)

    assert claude.calls == ["https://uni.example/detail/3"]
    assert summary.pages_skipped == 2  # detail/1 and detail/2 were read before and are unchanged


def test_changed_page_replaces_its_old_events(setup):
    Session, web, claude = setup
    run(Session, web, claude)
    web.pages["https://uni.example/detail/1"] = ("Workshop Git (เลื่อนวัน)", [])
    web.body["https://uni.example/detail/1"] = "เลื่อนเป็น 5 ธ.ค."
    web.body[LISTING] = "listing changed too"

    run(Session, web, claude)

    with Session() as db:
        names = sorted(db.scalars(select(EventRow.name)))
    assert names == ["Workshop Git (เลื่อนวัน)", "หลักสูตรพยาบาล"]  # old name is gone, no duplicates


def test_failed_page_is_retried_next_run(setup):
    Session, web, claude = setup
    claude.fail_on.add("https://uni.example/detail/2")
    first = run(Session, web, claude)
    assert len(first.errors) == 1
    assert "error" in kinds(Session)

    claude.fail_on.clear()
    claude.calls.clear()
    run(Session, web, claude)

    # The listing hash wasn't saved because of the failure, so detail/2 is tried again.
    assert claude.calls == ["https://uni.example/detail/2"]


def test_broken_source_is_logged_not_crashed(setup):
    Session, web, claude = setup
    del web.pages[LISTING]

    summary = run(Session, web, claude)

    assert summary.errors and "เปิดหน้า" in summary.errors[0]
    assert kinds(Session) == ["error"]


def test_short_title_drops_site_name():
    from src.pipeline import short_title
    assert short_title("Workshop Git | Mae Fah Luang University") == "Workshop Git"
    assert short_title("28-29 ม.ค. | Aquatic Exercise | MFU") == "28-29 ม.ค. | Aquatic Exercise"
    assert short_title("No site name") == "No site name"
    assert short_title(None) == "(ไม่มีชื่อ)"
