# Scout — your campus event agent

> Draft. Target length: ~200–300 words. Simple English is fine.
> Fill in `[ ]` before submitting. Do not add numbers we have not measured.

**Team:** [team name] · [member names] · Mae Fah Luang University, Thailand
**Quest:** AI Agents — "Agent Mode: ON"
**Demo:** [live URL] · **Code:** [repo URL, optional]

## The problem
University students miss activities, workshops and deadlines because news is spread across many web pages and emails. Even after signing up, they still have to copy dates into a calendar, notice when organisers move an event, and remember what to bring.

## What Scout does
Scout is an AI agent that does this job for each student, every day:
1. **Reads** the university news website (and any page the student adds) and the emails about events the student signed up for.
2. **Extracts** event details (date, deadline, place, fee, who can join) with Claude structured output. If a detail is not in the text, Scout leaves it empty instead of guessing.
3. **Checks eligibility** with plain code (age, level, fee). When information is missing, it says "unsure" instead of hiding the event.
4. **Manages the calendar:** adds draft events, moves an event when the organiser reschedules, and sets reminders.
5. **Reports** what it did on a timeline, and asks the student before bigger actions.
6. **Takes plain-language commands** in the app or Telegram, e.g. "find events this month that give activity hours".

## How we keep the agent safe
- Clear autonomy rules: small actions are done automatically and can be undone; bigger actions need approval; Scout never submits applications, sends emails or logs in for the user.
- Every action is logged with a reason and a link to the source.
- Web pages and emails are treated as data, never as instructions (prompt injection).
- Read-only Gmail access, raw emails are not stored, and users can delete their account (Thailand PDPA).

## How we tested it (before → after)
We tried to break Scout with [N] test cases (missing info, rescheduled events, prompt injection, unchanged pages, ...). Results are in our test scoreboard: [before]% → [after]% passed.

## Results with real users
[N] students outside our friend group used Scout for [N] days. [Key numbers from PROJECT_BRIEF section 7, e.g. extraction accuracy, % of auto-actions not undone, time saved.]

## AI tools we used
Claude API (inside Scout) and Claude Code (coding assistant). Details in our AI tools credit.
