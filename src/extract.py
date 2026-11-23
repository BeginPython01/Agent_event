"""Send a RawDocument to Claude and get back a list of Event objects.

Why structured output (messages.parse + a Pydantic model)?
Claude is forced to answer in exactly our JSON shape, and the SDK turns the
JSON into Event objects for us. No fragile "find the JSON in the text" code.
"""

import os
from dataclasses import dataclass
from datetime import date

import anthropic

from src.models import Event, ExtractionResult, RawDocument

DEFAULT_MODEL = "claude-haiku-5-5"

SYSTEM_PROMPT = """You extract upcoming opportunities for students (hackathons, workshops, camps, competitions, talks) from web pages and emails. Text may be in Thai, English, or both.

Rules:
- Only extract what the text actually says. If a field is not stated, use null. Never guess or invent values. A wrong deadline is worse than a missing one, because a student may miss the event.
- Return every distinct event in the text. If the text has no event, return an empty list.
- Dates: output ISO format (YYYY-MM-DD) in the Gregorian calendar. Thai Buddhist years (พ.ศ.) must be converted by subtracting 543. If the year is missing, use the next occurrence of that date on or after today's date, and lower the confidence.
- registration_deadline is the last day to apply/register, not the event day. If only "register by event day" is implied, leave it null.
- register_url must be an absolute URL taken from the text or the link list. Prefer an application form or sign-up page over a general homepage.
- fee_amount: 0 only if the text says it is free; null if fees are not mentioned.
- confidence: 1.0 when the value is stated clearly, around 0.5 when you had to interpret it (missing year, vague wording), 0.0 when the field is null."""


@dataclass
class ExtractOutput:
    events: list[Event]
    input_tokens: int  # kept for the cost metric later
    output_tokens: int


class ExtractError(Exception):
    """Raised when Claude could not give us a usable answer."""


def _build_user_message(doc: RawDocument, today: date) -> str:
    links = "\n".join(doc.links) if doc.links else "(none)"
    # Put today's date here, not in SYSTEM_PROMPT, so the system prompt never
    # changes and can be cached later.
    return (
        f"Today's date: {today.isoformat()}\n"
        f"Source: {doc.source_ref}\n"
        f"Title: {doc.title or '(none)'}\n\n"
        f"<text>\n{doc.text}\n</text>\n\n"
        f"<links>\n{links}\n</links>"
    )


def extract_events(
    doc: RawDocument,
    client: anthropic.Anthropic | None = None,
    today: date | None = None,
) -> ExtractOutput:
    """Ask Claude to pull events out of one document.

    `client` and `today` are parameters so tests can pass a fake client and a
    fixed date. In normal use you leave them out.
    """
    client = client or anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    model = os.getenv("CLAUDE_MODEL") or DEFAULT_MODEL
    today = today or date.today()

    response = client.messages.parse(
        model=model,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_message(doc, today)}],
        output_format=ExtractionResult,
        # Extraction is a simple task: low effort = less thinking = cheaper and faster.
        output_config={"effort": "low"},
    )

    # Always check why Claude stopped before trusting the output.
    if response.stop_reason == "max_tokens":
        raise ExtractError("Answer was cut off (max_tokens). The page may list too many events.")
    if response.stop_reason == "refusal":
        raise ExtractError(f"Claude declined this document: {response.stop_details}")
    if response.parsed_output is None:
        raise ExtractError(f"No structured output returned (stop_reason={response.stop_reason})")

    events = response.parsed_output.events
    for event in events:
        event.source_ref = doc.source_ref  # set by code, not by the LLM, so it's always right

    return ExtractOutput(
        events=events,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
