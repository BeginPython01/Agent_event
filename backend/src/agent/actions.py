"""Scout's action log (the timeline the user sees).

Every time Scout does something, it writes one AgentAction row here: what it
did, why, and where the information came from. This is what makes the agent
explainable, and later (Phase 3) it's also what makes "undo" possible.
"""

from sqlalchemy.orm import Session

from src.db import AgentAction


def log_action(
    session: Session,
    user_ids: list[int],
    kind: str,
    summary: str,
    reason: str | None = None,
    source_ref: str | None = None,
    autonomy: str = "auto",
    undo_payload: dict | None = None,
) -> None:
    """Write the same action to the timeline of every user it concerns.

    One page can be watched by many users, so one fetch can be news for all of
    them. Each user gets their own row so they can each see (and later undo)
    it on their own timeline.
    """
    for user_id in user_ids:
        session.add(AgentAction(
            user_id=user_id,
            kind=kind,
            summary=summary,
            reason=reason,
            source_ref=source_ref,
            autonomy=autonomy,
            undo_payload=undo_payload,
        ))
