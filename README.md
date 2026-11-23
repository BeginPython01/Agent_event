# Scout — Campus Event Agent

AI agent that follows university activities and emails about events you signed up for, keeps your calendar up to date, and tells you what needs your decision. See `PROJECT_BRIEF.md` for the full plan.

**Status:** Phase 2 (FastAPI + database + eligibility + agent log)

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env  — then add ANTHROPIC_API_KEY
```

## Usage (from `backend/`)

```bash
uvicorn src.api.app:app --reload     # API; open http://127.0.0.1:8000/docs
python -m src.pipeline               # one Scout run over every watched URL
python -m src.main --url https://mfu.ac.th/news/news-seminar.html --follow news-detail --max 3
```

Quick try in `/docs`: `POST /users` → copy the id → use it as the `X-User-Id` header →
`POST /me/watched-urls` → `POST /runs` → `GET /me/events` and `GET /me/actions`.

## Tests

```bash
python -m pytest -q
```

Tests use a fake Claude client, a fake website and a temporary database: no internet, no API key.

## Project layout

```
PROJECT_BRIEF.md   plan, rules, decisions (read first)
CLAUDE.md          instructions for Claude Code
docs/prompts/      frontend prompt (Phase 4)
backend/
  src/
    models.py        Pydantic models
    sources/web.py   URL -> RawDocument (robots.txt, <main> only, follow listing links)
    extract.py       RawDocument -> list[Event] via Claude structured output
    eligibility.py   can this user join? (plain code)
    db.py            SQLAlchemy tables
    pipeline.py      one Scout run: hash check -> extract -> save -> log
    agent/actions.py Scout's timeline
    api/             FastAPI app
  tests/  data/
```
