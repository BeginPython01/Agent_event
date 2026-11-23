"""Command line entry point.

Usage:
    # one page
    python -m src.main --url https://example.com/hackathon

    # a listing page: follow links that match a pattern, read each detail page
    python -m src.main --url https://mfu.ac.th/news/news-seminar.html --follow news-detail --max 3

    # raw JSON instead of a summary
    python -m src.main --url ... --json
"""

import argparse
import json
import os
import sys

import anthropic
from dotenv import load_dotenv

from src.extract import ExtractError, extract_events
from src.models import Event
from src.sources.web import FetchError, fetch_listing, fetch_url

# Haiku 5.5 price per 1M tokens (prompts up to 100K tokens). Used only for a rough estimate.
PRICE_INPUT_PER_M = 0.10
PRICE_OUTPUT_PER_M = 0.50


def format_event(i: int, e: Event) -> str:
    el = e.eligibility
    c = e.confidence
    fee = "?" if e.fee_amount is None else ("free" if e.fee_amount == 0 else f"{e.fee_amount} {e.fee_currency or ''}")
    where = e.location or "?"
    if e.is_online:
        where += " (online)"
    lines = [
        f"[{i}] {e.name}  ({e.category}{', campus' if e.is_campus else ''})",
        f"    Organizer: {e.organizer or '?'}",
        f"    Deadline : {e.registration_deadline or '?'}   (confidence {c.registration_deadline:.2f})",
        f"    Dates    : {e.event_start or '?'} -> {e.event_end or '?'}   (confidence {c.event_dates:.2f})",
        f"    Where    : {where}",
        f"    Fee      : {fee}",
        f"    Register : {e.register_url or '?'}",
        f"    Eligible : age {el.age_min or '-'}-{el.age_max or '-'}, levels {el.allowed_levels or 'any'}, "
        f"majors {el.allowed_majors or 'any'}, nationality {el.nationality or 'any'}, "
        f"team {el.team_size_min or '-'}-{el.team_size_max or '-'}   (confidence {c.eligibility:.2f})",
    ]
    if e.activity_hours is not None:
        lines.append(f"    Hours    : {e.activity_hours} activity hours")
    if el.other_conditions:
        lines.append(f"    Other    : {el.other_conditions}")
    if e.prizes_or_benefits:
        lines.append(f"    Benefits : {e.prizes_or_benefits}")
    lines.append(f"    Source   : {e.source_ref}")
    return "\n".join(lines)


def main() -> int:
    load_dotenv()  # loads ANTHROPIC_API_KEY etc. from .env

    parser = argparse.ArgumentParser(description="Extract events from web pages with Claude.")
    parser.add_argument("--url", required=True, help="An event page, or a listing page with --follow")
    parser.add_argument("--follow", metavar="PATTERN", help="Regex for detail links to follow, e.g. news-detail")
    parser.add_argument("--max", type=int, default=5, help="Max detail pages to read with --follow (default 5)")
    parser.add_argument("--json", action="store_true", help="Print raw JSON instead of a summary")
    args = parser.parse_args()

    # Fail fast with a clear message, before we spend time fetching pages.
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.", file=sys.stderr)
        return 1

    try:
        docs = fetch_listing(args.url, args.follow, args.max) if args.follow else [fetch_url(args.url)]
    except FetchError as e:
        print(f"Fetch error: {e}", file=sys.stderr)
        return 1

    client = anthropic.Anthropic()  # one client, reused for every page
    events: list[Event] = []
    input_tokens = output_tokens = skipped_past = 0
    for doc in docs:
        print(f"Reading '{doc.title}' ({len(doc.text):,} chars)", file=sys.stderr)
        try:
            result = extract_events(doc, client=client)
        except ExtractError as e:
            print(f"  Extract error: {e}", file=sys.stderr)
            continue
        except anthropic.AuthenticationError:
            print("Claude API key is missing or invalid. Check ANTHROPIC_API_KEY in .env", file=sys.stderr)
            return 1
        except anthropic.APIError as e:
            print(f"  Claude API error: {e}", file=sys.stderr)
            continue
        events.extend(result.events)
        input_tokens += result.input_tokens
        output_tokens += result.output_tokens
        skipped_past += result.skipped_past

    if args.json:
        print(json.dumps([e.model_dump(mode="json") for e in events], indent=2, ensure_ascii=False))
    else:
        if not events:
            print("No upcoming events found.")
        for i, event in enumerate(events, start=1):
            print(format_event(i, event))
            print()

    cost = input_tokens / 1e6 * PRICE_INPUT_PER_M + output_tokens / 1e6 * PRICE_OUTPUT_PER_M
    print(
        f"Pages: {len(docs)} · events: {len(events)} · skipped (already past): {skipped_past}\n"
        f"Tokens: {input_tokens:,} in / {output_tokens:,} out  (~${cost:.5f})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
