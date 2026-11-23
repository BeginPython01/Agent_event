"""Data models shared by every part of the app.

We use Pydantic because:
- it validates data for us (e.g. a date string really is a date)
- the same class can be handed to Claude as a JSON schema (structured output)
"""

from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# RawDocument: what every source (web, email, ...) returns.
# Keeping one shape means the pipeline never cares where text came from.
# ---------------------------------------------------------------------------
class RawDocument(BaseModel):
    source_type: Literal["web", "email"]
    source_ref: str  # URL or email message id
    title: str | None = None
    sender: str | None = None  # email only
    text: str
    links: list[str] = []
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Event: what Claude extracts. Every field is optional (None) because
# the rule is "if it is not in the text, leave it null - never guess".
# The descriptions are sent to Claude as part of the schema, so they double
# as instructions.
# ---------------------------------------------------------------------------
StudyLevel = Literal[
    "high_school",  # includes pre-U / junior college / ม.ปลาย
    "vocational",  # includes polytechnic / ปวช. / ปวส.
    "undergraduate",  # ปริญญาตรี
    "postgraduate",  # ป.โท / ป.เอก
    "working",  # working professionals
    "other",
]


class Eligibility(BaseModel):
    age_min: int | None = Field(None, description="Minimum age in years, if stated")
    age_max: int | None = Field(None, description="Maximum age in years, if stated")
    birth_year_min: int | None = Field(
        None, description="Earliest allowed birth year (Gregorian), if stated"
    )
    birth_year_max: int | None = Field(
        None, description="Latest allowed birth year (Gregorian), if stated"
    )
    student_only: bool | None = Field(
        None, description="True if only students may join, False if explicitly open to all"
    )
    allowed_levels: list[StudyLevel] | None = Field(
        None, description="Education levels allowed to join. null if not stated"
    )
    allowed_majors: list[str] | None = Field(
        None, description="Fields of study allowed, e.g. ['Computer Science']. null if any/not stated"
    )
    nationality: list[str] | None = Field(
        None, description="Allowed nationalities or residency, e.g. ['Thai']. null if not stated"
    )
    team_size_min: int | None = None
    team_size_max: int | None = None
    other_conditions: str | None = Field(
        None, description="Any other requirement in plain words, copied briefly from the text"
    )


class FieldConfidence(BaseModel):
    """How sure Claude is (0.0-1.0) about the fields that matter most."""

    registration_deadline: float = Field(description="0.0 = not found/guess, 1.0 = stated exactly")
    event_dates: float = Field(description="Confidence for event_start/event_end, 0.0-1.0")
    eligibility: float = Field(description="Confidence for the eligibility block, 0.0-1.0")


class Event(BaseModel):
    name: str
    category: Literal["hackathon", "workshop", "camp", "competition", "talk", "other"]
    event_start: date | None = None
    event_end: date | None = None
    registration_deadline: date | None = Field(
        None, description="Last day to register/apply. The most important field."
    )
    location: str | None = None
    is_online: bool | None = None
    fee_amount: float | None = Field(None, description="0 if explicitly free, null if not stated")
    fee_currency: str | None = Field(None, description="ISO code like THB, SGD, USD")
    register_url: str | None = Field(None, description="Absolute URL to the registration page")
    eligibility: Eligibility
    prizes_or_benefits: str | None = None
    source_ref: str | None = Field(None, description="Leave null; filled in by the program")
    confidence: FieldConfidence


class ExtractionResult(BaseModel):
    """Top-level object Claude returns: a page can list zero, one or many events."""

    events: list[Event]


# ---------------------------------------------------------------------------
# UserProfile and EligibilityResult: used from Phase 2 onwards.
# Defined now so the shapes are agreed early.
# ---------------------------------------------------------------------------
class UserProfile(BaseModel):
    birth_year: int | None = None
    university: str | None = None
    level: StudyLevel | None = None
    year_of_study: int | None = None
    major: str | None = None
    nationality: str | None = None
    max_fee: float | None = None
    interests: list[str] = []
    telegram_chat_id: int | None = None


class EligibilityResult(BaseModel):
    status: Literal["eligible", "not_eligible", "unsure"]
    reasons: list[str] = []
