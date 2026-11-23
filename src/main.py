"""Command line entry point.

Usage:
    python -m src.main --url https://example.com/hackathon
    python -m src.main --url https://example.com/hackathon --json
"""

import argparse
import json
import os
import sys

import anthropic
from dotenv import load_dotenv

from src.extract import ExtractError, extract_events
from src.models import Event
from src.sources.web import FetchError, fetch_url

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
        f"[{i}] {e.name}  ({e.category})",
        f"    Deadline : {e.registration_deadline or '?'}   (confidence {c.registration_deadline:.2f})",
        f"    Dates    : {e.event_start or '?'} -> {e.event_end or '?'}   (confidence {c.event_dates:.2f})",
        f"    Where    : {where}",
        f"    Fee      : {fee}",
        f"    Register : {e.register_url or '?'}",
        f"    Eligible : age {el.age_min or '-'}-{el.age_max or '-'}, levels {el.allowed_levels or 'any'}, "
        f"majors {el.allowed_majors or 'any'}, nationality {el.nationality or 'any'}, "
        f"team {el.team_size_min or '-'}-{el.team_size_max or '-'}   (confidence {c.eligibility:.2f})",
    ]
    if el.other_conditions:
        lines.append(f"    Other    : {el.other_conditions}")
    if e.prizes_or_benefits:
        lines.append(f"    Benefits : {e.prizes_or_benefits}")
    lines.append(f"    Source   : {e.source_ref}")
    return "\n".join(lines)


def main() -> int:
    load_dotenv()  # loads ANTHROPIC_API_KEY etc. from .env

    parser = argparse.ArgumentParser(description="Extract events from a web page with Claude.")
    parser.add_argument("--url", required=True, help="Page that lists one or more events")
    parser.add_argument("--json", action="store_true", help="Print raw JSON instead of a summary")
    args = parser.parse_args()

    # Fail fast with a clear message, before we spend time fetching the page.
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.", file=sys.stderr)
        return 1

    try:
        doc = fetch_url(args.url)
        print(f"Fetched '{doc.title}' ({len(doc.text):,} chars, {len(doc.links)} links)", file=sys.stderr)
        result = extract_events(doc)
    except FetchError as e:
        print(f"Fetch error: {e}", file=sys.stderr)
        return 1
    except ExtractError as e:
        print(f"Extract error: {e}", file=sys.stderr)
        return 1
    except anthropic.AuthenticationError:
        print("Claude API key is missing or invalid. Check ANTHROPIC_API_KEY in .env", file=sys.stderr)
        return 1
    except anthropic.APIError as e:
        print(f"Claude API error: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps([e.model_dump(mode="json") for e in result.events], indent=2, ensure_ascii=False))
    else:
        if not result.events:
            print("No events found on this page.")
        for i, event in enumerate(result.events, start=1):
            print(format_event(i, event))
            print()

    cost = result.input_tokens / 1e6 * PRICE_INPUT_PER_M + result.output_tokens / 1e6 * PRICE_OUTPUT_PER_M
    print(
        f"Tokens: {result.input_tokens:,} in / {result.output_tokens:,} out  (~${cost:.5f})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
