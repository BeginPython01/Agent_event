"""Scout REST API.

Run locally (from the backend/ folder):
    uvicorn src.api.app:app --reload
then open http://127.0.0.1:8000/docs to try every endpoint in the browser.

Who is "me"? Until Google login arrives in Phase 4, the caller says which
user they are with an `X-User-Id` header. That is fine for development and
NOT safe for real users, so it will be replaced, not kept.
"""

from collections.abc import Iterator
from dataclasses import asdict
from datetime import date

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.schemas import (
    AgentActionOut, ApplicationIn, ApplicationOut, CreatedUser, EventOut, RunSummaryOut, WatchedUrlIn, WatchedUrlOut,
)
from src.db import AgentAction, Application, EventRow, SourceDocument, User, WatchedUrl, make_session_factory, user_profile
from src.eligibility import check_eligibility
from src.extract import is_past
from src.models import Event, UserProfile
from src.pipeline import run_pipeline


def create_app(database_url: str | None = None) -> FastAPI:
    """Build the app. Tests call this with a temporary database."""
    load_dotenv()
    app = FastAPI(title="Scout API", description="Campus event agent: backend for the web app.")
    app.state.session_factory = make_session_factory(database_url)

    # ---- dependencies (FastAPI runs these before each request) -------------
    def get_db(request: Request) -> Iterator[Session]:
        with request.app.state.session_factory() as session:
            yield session

    def current_user(x_user_id: int = Header(description="Dev-only login. Replaced by Google login in Phase 4."),
                     db: Session = Depends(get_db)) -> User:
        user = db.get(User, x_user_id)
        if user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found. Create one with POST /users")
        return user

    # ---- users & profile ----------------------------------------------------
    @app.get("/health")
    def health() -> dict:
        return {"ok": True}

    @app.post("/users", response_model=CreatedUser, status_code=201, tags=["users"])
    def create_user(profile: UserProfile | None = None, db: Session = Depends(get_db)):
        user = User(**(profile or UserProfile()).model_dump())
        db.add(user)
        db.commit()
        return CreatedUser(id=user.id)

    @app.get("/me/profile", response_model=UserProfile, tags=["users"])
    def get_profile(user: User = Depends(current_user)):
        return user_profile(user)

    @app.put("/me/profile", response_model=UserProfile, tags=["users"])
    def update_profile(profile: UserProfile, user: User = Depends(current_user), db: Session = Depends(get_db)):
        for key, value in profile.model_dump().items():
            setattr(user, key, value)
        db.commit()
        return user_profile(user)

    @app.delete("/me", status_code=204, tags=["users"])
    def delete_me(user: User = Depends(current_user), db: Session = Depends(get_db)):
        """PDPA: delete the user and everything linked to them."""
        db.delete(user)
        db.commit()

    # ---- watched URLs -------------------------------------------------------
    @app.get("/me/watched-urls", response_model=list[WatchedUrlOut], tags=["sources"])
    def list_watched(user: User = Depends(current_user), db: Session = Depends(get_db)):
        return db.scalars(select(WatchedUrl).where(WatchedUrl.user_id == user.id).order_by(WatchedUrl.id)).all()

    @app.post("/me/watched-urls", response_model=WatchedUrlOut, status_code=201, tags=["sources"])
    def add_watched(body: WatchedUrlIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
        watched = WatchedUrl(user_id=user.id, **body.model_dump())
        db.add(watched)
        try:
            db.commit()
        except IntegrityError:
            raise HTTPException(status.HTTP_409_CONFLICT, "You already watch this URL")
        return watched

    @app.delete("/me/watched-urls/{watched_id}", status_code=204, tags=["sources"])
    def remove_watched(watched_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
        watched = db.get(WatchedUrl, watched_id)
        if watched is None or watched.user_id != user.id:  # never let one user touch another's data
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
        db.delete(watched)
        db.commit()

    # ---- events feed --------------------------------------------------------
    @app.get("/me/events", response_model=list[EventOut], tags=["events"])
    def my_events(include_not_eligible: bool = False, user: User = Depends(current_user), db: Session = Depends(get_db)):
        """Upcoming events from the user's sources, each with an eligibility check.

        Eligibility is computed here on every request instead of being stored:
        it's plain code and fast, and the answer stays right when the user
        edits their profile.
        """
        urls = [w.url for w in db.scalars(select(WatchedUrl).where(WatchedUrl.user_id == user.id))]
        if not urls:
            return []
        rows = db.scalars(
            select(EventRow).join(SourceDocument)
            .where(or_(SourceDocument.found_via.in_(urls), SourceDocument.source_ref.in_(urls)))
        ).all()
        lanes = {a.event_id: a.lane for a in db.scalars(select(Application).where(Application.user_id == user.id))}
        profile = user_profile(user)
        today = date.today()

        results = []
        for row in rows:
            event = Event.model_validate(row.data)
            if is_past(event, today):
                continue
            eligibility = check_eligibility(event, profile, today)
            if eligibility.status == "not_eligible" and not include_not_eligible:
                continue
            results.append(EventOut(id=row.id, event=event, eligibility=eligibility, lane=lanes.get(row.id)))
        # Soonest deadline first; events without a deadline go last.
        results.sort(key=lambda r: (r.event.registration_deadline or date.max, r.event.event_start or date.max))
        return results

    # ---- applications board -------------------------------------------------
    @app.get("/me/applications", response_model=list[ApplicationOut], tags=["applications"])
    def list_applications(user: User = Depends(current_user), db: Session = Depends(get_db)):
        rows = db.execute(
            select(Application, EventRow.name).join(EventRow).where(Application.user_id == user.id)
        ).all()
        return [ApplicationOut(id=a.id, event_id=a.event_id, lane=a.lane, event_name=name, updated_at=a.updated_at)
                for a, name in rows]

    @app.put("/me/applications", response_model=ApplicationOut, tags=["applications"])
    def set_application(body: ApplicationIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
        """Put an event on the board, or move it to another lane."""
        event_row = db.get(EventRow, body.event_id)
        if event_row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
        app_row = db.scalar(select(Application).where(Application.user_id == user.id,
                                                       Application.event_id == body.event_id))
        if app_row is None:
            app_row = Application(user_id=user.id, event_id=body.event_id, lane=body.lane)
            db.add(app_row)
        else:
            app_row.lane = body.lane
        db.commit()
        return ApplicationOut(id=app_row.id, event_id=app_row.event_id, lane=app_row.lane,
                              event_name=event_row.name, updated_at=app_row.updated_at)

    # ---- Scout's timeline ---------------------------------------------------
    @app.get("/me/actions", response_model=list[AgentActionOut], tags=["agent"])
    def my_actions(limit: int = 50, user: User = Depends(current_user), db: Session = Depends(get_db)):
        return db.scalars(
            select(AgentAction).where(AgentAction.user_id == user.id)
            .order_by(AgentAction.created_at.desc(), AgentAction.id.desc()).limit(min(limit, 200))
        ).all()

    # ---- run Scout now (development) ----------------------------------------
    @app.post("/runs", response_model=RunSummaryOut, tags=["agent"])
    def run_now(db: Session = Depends(get_db)):
        """Run the pipeline for every user. In production this is the twice-a-day cron job."""
        return RunSummaryOut(**asdict(run_pipeline(db)))

    return app


app = create_app()
