"""Tests for src/extract.py using a fake Claude client (no API key, no cost)."""

from datetime import date
from types import SimpleNamespace

import pytest

from src.extract import ExtractError, extract_events
from src.models import Eligibility, Event, ExtractionResult, FieldConfidence, RawDocument

DOC = RawDocument(source_type="web", source_ref="https://example.com/e", title="T", text="some event text")


class FakeMessages:
    """Pretends to be client.messages. Remembers what it was called with."""

    def __init__(self, response):
        self.response = response
        self.called_with = None

    def parse(self, **kwargs):
        self.called_with = kwargs
        return self.response


def fake_client(parsed=None, stop_reason="end_turn"):
    response = SimpleNamespace(
        parsed_output=parsed,
        stop_reason=stop_reason,
        stop_details=None,
        usage=SimpleNamespace(input_tokens=1234, output_tokens=56),
    )
    return SimpleNamespace(messages=FakeMessages(response))


def sample_event() -> Event:
    return Event(
        name="MFU Hackathon 2027",
        category="hackathon",
        registration_deadline=date(2027, 1, 31),
        eligibility=Eligibility(allowed_levels=["undergraduate"]),
        confidence=FieldConfidence(registration_deadline=1.0, event_dates=1.0, eligibility=0.9),
    )


def test_returns_events_and_sets_source_ref():
    client = fake_client(ExtractionResult(events=[sample_event()]))

    out = extract_events(DOC, client=client, today=date(2026, 11, 23))

    assert len(out.events) == 1
    assert out.events[0].source_ref == "https://example.com/e"  # filled by code
    assert out.input_tokens == 1234


def test_sends_todays_date_and_text_to_claude():
    client = fake_client(ExtractionResult(events=[]))

    extract_events(DOC, client=client, today=date(2026, 11, 23))

    user_msg = client.messages.called_with["messages"][0]["content"]
    assert "Today's date: 2026-11-23" in user_msg
    assert "some event text" in user_msg
    assert client.messages.called_with["output_format"] is ExtractionResult


def test_max_tokens_raises():
    client = fake_client(None, stop_reason="max_tokens")
    with pytest.raises(ExtractError):
        extract_events(DOC, client=client)


def test_refusal_raises():
    client = fake_client(None, stop_reason="refusal")
    with pytest.raises(ExtractError):
        extract_events(DOC, client=client)


def test_past_events_are_dropped_by_code():
    past = sample_event()
    past.name = "Old event"
    past.registration_deadline = date(2026, 10, 1)
    no_dates = sample_event()
    no_dates.name = "No dates"
    no_dates.registration_deadline = None
    client = fake_client(ExtractionResult(events=[sample_event(), past, no_dates]))

    out = extract_events(DOC, client=client, today=date(2026, 11, 23))

    names = [e.name for e in out.events]
    assert names == ["MFU Hackathon 2027", "No dates"]  # unknown dates are kept, not dropped
    assert out.skipped_past == 1
