"""One Scout run: read every watched page, extract what's new, log it all.

    watched URLs ─> fetch ─> same hash as last time? ─yes─> skip (no LLM, logged)
                                     │no
                                     ▼
                              Claude extract ─> save events ─> eligibility ─> log

Run it with:  python -m src.pipeline
(Later, GitHub Actions will run this twice a day.)

`fetch` and `extract` are parameters so tests can pass fakes: no internet,
no API key, and we can count exactly how many times the LLM was called.
"""

import hashlib
import os
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

import anthropic
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.agent.actions import log_action
from src.db import EventRow, SourceDocument, User, WatchedUrl, make_session_factory, user_profile, utcnow
from src.eligibility import check_eligibility
from src.extract import ExtractError, ExtractOutput, extract_events
from src.models import Event, RawDocument
from src.sources.web import DELAY_BETWEEN_REQUESTS, FetchError, fetch_url, find_detail_links

Fetcher = Callable[[str], RawDocument]
Extractor = Callable[[RawDocument], ExtractOutput]


@dataclass
class RunSummary:
    pages_read: int = 0
    pages_skipped: int = 0  # unchanged since last run -> no LLM call
    llm_calls: int = 0
    events_saved: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    errors: list[str] = field(default_factory=list)


def short_title(title: str | None) -> str:
    """"Workshop Git | Mae Fah Luang University" -> "Workshop Git".

    Most sites add their own name after the last " | ". On a timeline that's
    just noise, so we drop it (only when there's something left before it).
    """
    if not title:
        return "(ไม่มีชื่อ)"
    head, sep, _site = title.rpartition(" | ")
    return head.strip() if sep and head.strip() else title.strip()


def text_hash(text: str) -> str:
    """A short fingerprint of the page text. Same text -> same hash."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class _Run:
    """Holds what one run needs, so the helper methods don't pass 6 arguments around."""

    def __init__(self, session: Session, fetch: Fetcher, extract: Extractor, today: date, delay: float):
        self.session = session
        self.fetch = fetch
        self.extract = extract
        self.today = today
        self.delay = delay
        self.summary = RunSummary()

    # -- one watched URL (shared by one or more users) ------------------------
    def process_source(self, url: str, pattern: str | None, max_items: int, watchers: list[int]) -> None:
        doc = self.fetch(url)
        self.summary.pages_read += 1

        if pattern is None:
            # The URL is itself an event page.
            new_events = []
            status = self.process_document(doc, found_via=url, watchers=watchers, new_events=new_events)
            if status == "unchanged":
                log_action(self.session, watchers, "skip_unchanged",
                           f"หน้า “{short_title(doc.title)}” ไม่มีอะไรเปลี่ยน ข้ามการเรียก AI", source_ref=url)
            self.log_filtered(new_events, watchers)
            return

        # A listing page: if the list itself didn't change, there is nothing new to follow.
        listing = self.session.scalar(select(SourceDocument).where(SourceDocument.source_ref == url))
        listing_hash = text_hash(doc.text)
        if listing and listing.content_hash == listing_hash:
            listing.last_checked_at = utcnow()
            self.summary.pages_skipped += 1
            log_action(self.session, watchers, "skip_unchanged",
                       f"หน้า “{short_title(doc.title)}” ไม่มีอะไรเปลี่ยน ข้ามการเรียก AI", source_ref=url)
            return

        detail_urls = find_detail_links(doc, pattern, max_items)
        log_action(self.session, watchers, "read_source",
                   f"อ่านหน้า “{short_title(doc.title)}” เจอลิงก์ {len(detail_urls)} ลิงก์", source_ref=url)

        all_ok = True
        unchanged = 0
        new_events: list[EventRow] = []
        for detail_url in detail_urls:
            time.sleep(self.delay)
            try:
                detail = self.fetch(detail_url)
                self.summary.pages_read += 1
            except FetchError as e:
                all_ok = False
                self.error(watchers, f"เปิดหน้า {detail_url} ไม่ได้", str(e), detail_url)
                continue
            status = self.process_document(detail, found_via=url, watchers=watchers, new_events=new_events)
            all_ok = all_ok and status != "error"
            unchanged += status == "unchanged"

        if unchanged:
            log_action(self.session, watchers, "skip_unchanged",
                       f"{unchanged} หน้าเคยอ่านแล้วและไม่เปลี่ยน ข้ามการเรียก AI", source_ref=url)
        self.log_filtered(new_events, watchers)

        # Only remember the listing hash if every detail page worked. Otherwise
        # a page that failed today would be skipped forever.
        if all_ok:
            if listing is None:
                listing = SourceDocument(source_ref=url, found_via=url, is_listing=True)
                self.session.add(listing)
            listing.title = doc.title
            listing.content_hash = listing_hash
            listing.last_checked_at = utcnow()

    # -- one page that may contain events -------------------------------------
    def process_document(self, doc: RawDocument, found_via: str, watchers: list[int], new_events: list[EventRow]) -> str:
        """Returns "new", "unchanged" or "error"."""
        page_hash = text_hash(doc.text)
        saved = self.session.scalar(select(SourceDocument).where(SourceDocument.source_ref == doc.source_ref))
        if saved and saved.content_hash == page_hash:
            saved.last_checked_at = utcnow()
            self.summary.pages_skipped += 1
            return "unchanged"

        try:
            result = self.extract(doc)
        except (ExtractError, anthropic.APIError) as e:
            self.error(watchers, f"อ่าน “{short_title(doc.title)}” ไม่สำเร็จ", str(e), doc.source_ref)
            return "error"
        self.summary.llm_calls += 1
        self.summary.input_tokens += result.input_tokens
        self.summary.output_tokens += result.output_tokens

        if saved is None:
            saved = SourceDocument(source_ref=doc.source_ref, found_via=found_via)
            self.session.add(saved)
        else:
            # The page changed: its old events are replaced by what Claude read now.
            for old in self.session.scalars(select(EventRow).where(EventRow.document_id == saved.id)):
                self.session.delete(old)
        saved.title = doc.title
        saved.content_hash = page_hash
        saved.last_checked_at = utcnow()
        self.session.flush()  # gives `saved` an id so events can point to it

        for event in result.events:
            row = EventRow(
                document_id=saved.id, name=event.name, category=event.category,
                event_start=event.event_start, registration_deadline=event.registration_deadline,
                data=event.model_dump(mode="json"),
            )
            self.session.add(row)
            new_events.append(row)
        self.summary.events_saved += len(result.events)

        note = f" (ข้าม {result.skipped_past} งานที่จบไปแล้ว)" if result.skipped_past else ""
        log_action(self.session, watchers, "extract",
                   f"อ่าน “{short_title(doc.title)}” เจอ {len(result.events)} กิจกรรม{note}", source_ref=doc.source_ref)
        return "new"

    # -- helpers -------------------------------------------------------------
    def log_filtered(self, new_events: list[EventRow], watchers: list[int]) -> None:
        """Tell each user how many of the NEW events they can't join, and why."""
        if not new_events:
            return
        for user_id in watchers:
            profile = user_profile(self.session.get(User, user_id))
            blocked = []
            for row in new_events:
                result = check_eligibility(Event.model_validate(row.data), profile, self.today)
                if result.status == "not_eligible":
                    blocked.append(f"{row.name}: {result.reasons[0]}")
            if blocked:
                log_action(self.session, [user_id], "filter_out",
                           f"ตัดออก {len(blocked)} งานที่คุณสมัครไม่ได้", reason="\n".join(blocked))

    def error(self, watchers: list[int], summary: str, detail: str, source_ref: str) -> None:
        self.summary.errors.append(f"{summary}: {detail}")
        log_action(self.session, watchers, "error", summary, reason=detail, source_ref=source_ref)


def run_pipeline(
    session: Session,
    fetch: Fetcher = fetch_url,
    extract: Extractor | None = None,
    today: date | None = None,
    delay: float = DELAY_BETWEEN_REQUESTS,
) -> RunSummary:
    """Process every watched URL once. Commits at the end."""
    today = today or date.today()
    if extract is None:
        client: anthropic.Anthropic | None = None

        def extract(doc: RawDocument) -> ExtractOutput:
            # Create the client only when a page really changed, so a run where
            # everything is unchanged works even without an API key.
            nonlocal client
            if client is None and not os.getenv("ANTHROPIC_API_KEY"):
                # Without this check the SDK raises a TypeError that would crash the whole run.
                raise ExtractError("ANTHROPIC_API_KEY is not set (add it to .env)")
            client = client or anthropic.Anthropic()
            return extract_events(doc, client=client, today=today)

    # Many users may watch the same page: fetch it once, tell all of them.
    groups: dict[tuple[str, str | None, int], list[int]] = defaultdict(list)
    for watched in session.scalars(select(WatchedUrl).order_by(WatchedUrl.id)):
        groups[(watched.url, watched.follow_pattern, watched.max_items)].append(watched.user_id)

    run = _Run(session, fetch, extract, today, delay)
    for (url, pattern, max_items), watchers in groups.items():
        try:
            run.process_source(url, pattern, max_items, watchers)
        except FetchError as e:
            run.error(watchers, f"เปิดหน้า {url} ไม่ได้", str(e), url)
    session.commit()
    return run.summary


if __name__ == "__main__":
    load_dotenv()
    Session_ = make_session_factory()
    with Session_() as db:
        s = run_pipeline(db)
    print(f"pages read {s.pages_read}, skipped (unchanged) {s.pages_skipped}, LLM calls {s.llm_calls}, "
          f"events saved {s.events_saved}, errors {len(s.errors)}")
    for err in s.errors:
        print("  !", err)
