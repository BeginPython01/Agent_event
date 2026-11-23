# Event Scout Agent

Agent that finds upcoming student events (hackathons, workshops, camps, competitions) from web pages and email, checks whether you're eligible, and sends you the ones worth applying to. See `PROJECT_BRIEF.md` for the full plan.

**Status:** Phase 1 (web page → extract events with Claude)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then put your ANTHROPIC_API_KEY in .env
```

## Usage

```bash
python -m src.main --url https://example.com/some-hackathon
python -m src.main --url https://example.com/some-hackathon --json
```

## Tests

```bash
python -m pytest -q
```

Tests use a saved HTML file and a fake Claude client, so they need no internet and no API key.

## Project layout

```
src/
  models.py        Pydantic models (RawDocument, Event, UserProfile, ...)
  sources/web.py   URL -> RawDocument (robots.txt check, HTML -> text)
  extract.py       RawDocument -> list[Event] via Claude structured output
  main.py          CLI
tests/             unit tests
data/              sample pages for tests
metrics/           evaluation scripts (later phases)
```
