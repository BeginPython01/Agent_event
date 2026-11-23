"""Database tables and connection.

Why SQLAlchemy (an ORM) instead of raw SQL strings:
- queries are built for us with parameters, so SQL injection isn't possible
- the same code runs on SQLite today and on Postgres (Supabase) later:
  only DATABASE_URL changes

Tables are created automatically with create_all() for now. When the schema
starts changing often we'll add migrations (Alembic).
"""

import os
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from src.models import UserProfile


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # Profile fields mirror models.UserProfile
    birth_year: Mapped[int | None] = mapped_column(Integer)
    university: Mapped[str | None] = mapped_column(String(200))
    level: Mapped[str | None] = mapped_column(String(30))
    year_of_study: Mapped[int | None] = mapped_column(Integer)
    major: Mapped[str | None] = mapped_column(String(200))
    nationality: Mapped[str | None] = mapped_column(String(100))
    max_fee: Mapped[float | None] = mapped_column(Float)
    interests: Mapped[list] = mapped_column(JSON, default=list)


class WatchedUrl(Base):
    """A page one user asked Scout to follow."""

    __tablename__ = "watched_urls"
    __table_args__ = (UniqueConstraint("user_id", "url"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(1000))
    follow_pattern: Mapped[str | None] = mapped_column(String(200))  # e.g. "news-detail"
    max_items: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SourceDocument(Base):
    """One page we have read, shared by every user.

    `content_hash` is how we skip the LLM: if a page's text hash is the same
    as last time, nothing changed, so there is nothing new to extract.
    Sharing it across users means 20 people watching the MFU news page cost
    one LLM call, not twenty.
    """

    __tablename__ = "source_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_ref: Mapped[str] = mapped_column(String(1000), unique=True)
    found_via: Mapped[str] = mapped_column(String(1000))  # the watched URL that led us here
    is_listing: Mapped[bool] = mapped_column(default=False)
    title: Mapped[str | None] = mapped_column(String(500))
    content_hash: Mapped[str] = mapped_column(String(64))
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EventRow(Base):
    """An event Claude extracted. The full Event is kept as JSON in `data`;
    the columns we filter or sort by are copied out next to it."""

    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(30))
    event_start: Mapped[date | None] = mapped_column(Date)
    registration_deadline: Mapped[date | None] = mapped_column(Date)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Application(Base):
    """Where an event sits on the user's board (interested -> ... -> done)."""

    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "event_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    lane: Mapped[str] = mapped_column(String(30))
    source: Mapped[str] = mapped_column(String(20), default="manual")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AgentAction(Base):
    """One line on Scout's timeline: what it did, why, and how to undo it."""

    __tablename__ = "agent_actions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    kind: Mapped[str] = mapped_column(String(40))
    summary: Mapped[str] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    source_ref: Mapped[str | None] = mapped_column(String(1000))
    autonomy: Mapped[str] = mapped_column(String(20), default="auto")
    undo_payload: Mapped[dict | None] = mapped_column(JSON)


class NotificationChannel(Base):
    """Telegram / LINE ids. Used from Phase 5."""

    __tablename__ = "notification_channels"
    __table_args__ = (UniqueConstraint("user_id", "kind"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(20))  # "telegram" | "line"
    address: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


def user_profile(user: User) -> UserProfile:
    """Turn a database row into the Pydantic profile that eligibility.py expects."""
    return UserProfile(
        birth_year=user.birth_year, university=user.university, level=user.level,
        year_of_study=user.year_of_study, major=user.major, nationality=user.nationality,
        max_fee=user.max_fee, interests=user.interests or [],
    )


def make_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    """Connect to the database and make sure all tables exist."""
    url = database_url or os.getenv("DATABASE_URL") or "sqlite:///./scout.db"
    # SQLite + FastAPI: requests may run on different threads.
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args)
    if url.startswith("sqlite"):
        # SQLite ignores foreign keys unless asked. We need them so that
        # deleting a user really deletes their data (PDPA "delete me").
        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)
