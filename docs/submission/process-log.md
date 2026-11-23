# Process Log — Scout

> Rule: at least **5 dated entries** (University division). Written in English.
> Add one entry every working day/session. Write what we did, what AI did, and what we decided ourselves.
> If anyone (parent, teacher, friend) helped, write it here — this is required.
> Tip: spread entries over different dates; it shows real progress over time.

Template:
```
### YYYY-MM-DD — short title
- What we did:
- What AI tools did:
- Problem / what we learned:
- Decision we made (and why):
- Next step:
```

---

### 2026-11-23 — Idea and first prototype (Phase 1)
- What we did: Chose the AI Agents quest. Wrote a project brief. Built a first script that reads a Mae Fah Luang University news page and extracts event details.
- What AI tools did: Claude Code helped write the scraper and extraction code; Claude API extracts event fields with structured output.
- Problem / what we learned: University listing pages link to detail pages, so the agent must follow links. The site's robots.txt redirects to an HTML page, so we treat it as "no rules" while still waiting between requests.
- Decision: If a value is not in the text, store `null` — never invent it.
- Next step: Backend and database.

### 2026-11-23 — Changed direction to "agent-first"
- What we did: Redesigned the product from a simple event list into Scout, an agent that acts for the student and reports back.
- Decision: Small actions (draft calendar events, reminders) are automatic and can be undone; bigger actions need approval; Scout never submits forms or sends emails. Focus first on university activities and emails about events the student signed up for.
- Next step: Build the agent's action log.

### 2026-11-23 — Backend, database, eligibility, agent log (Phase 2)
- What we did: Built a FastAPI backend with a SQLite database (SQLAlchemy, so we can move to Postgres later), an eligibility checker in plain code, and the `AgentAction` timeline.
- What AI tools did: Claude Code helped write code and tests. Tests use a fake Claude, so they run without an API key.
- Decisions: Skip pages whose content hash has not changed (saves LLM cost). Eligibility returns `unsure` when information is missing instead of hiding the event. Pages read once are shared by all users.
- Next step: Gmail + Google Calendar.

### 2026-11-23 — Read the competition rules
- What we did: Read yai.sg rules and listed what we must submit; started this submission kit.
- Learned: Demo Weekend moved to 31 Jan 2027; the full challenge brief unlocks after registration, so we should register early.
- Next step: Register the team.

### [date] — [next entry]
