# AI Tools Used — Credit and Role

> YAI rule: credit every tool and explain what each one did. Update this list if we add tools.

| Tool | Used for | What the AI did | What we did ourselves |
|---|---|---|---|
| **Claude API** (model set in `.env`, default Claude Haiku) | Inside Scout | Extracts event details from web pages into structured data; [later] sorts emails (confirmed / rescheduled / result), understands plain-language commands with tool use | Designed the data model, prompts and rules (null if missing), checked results against our own answer set |
| **Claude Code** | Coding assistant | Suggested and wrote code, tests and explanations under our instructions | Planned features and phases, made design decisions, reviewed and tested the code, wrote the brief |
| [Claude chat / other] | [planning, mockups, ...] | [ ] | [ ] |

## Parts that use no AI (on purpose)
- **Eligibility check:** plain code, so decisions are predictable and explainable.
- **Autonomy rules:** fixed code table — the LLM cannot decide to do actions outside it.
- **Change detection:** content hash, no LLM.

## Human help
[List any help from teachers, parents, friends — must also appear in the process log. Write "None" if none.]
