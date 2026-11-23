"""Shapes of the data the API receives and sends back.

FastAPI reads these Pydantic classes to validate requests and to build the
interactive docs at /docs automatically.
"""

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from src.models import EligibilityResult, Event

Lane = Literal["interested", "drafting", "applied", "awaiting_result", "done"]


class WatchedUrlIn(BaseModel):
    url: str = Field(examples=["https://mfu.ac.th/news/news-seminar.html"])
    follow_pattern: str | None = Field(None, examples=["news-detail"],
                                       description="Regex for detail links. Leave empty if the URL is an event page.")
    max_items: int = Field(5, ge=1, le=20, description="How many detail pages to read per run")

    @field_validator("url")
    @classmethod
    def must_be_http(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return value

    @field_validator("follow_pattern")
    @classmethod
    def must_be_valid_regex(cls, value: str | None) -> str | None:
        if value:
            re.compile(value)  # raises a clear error now, instead of crashing a run later
        return value or None


class WatchedUrlOut(WatchedUrlIn):
    id: int
    created_at: datetime


class EventOut(BaseModel):
    id: int
    event: Event
    eligibility: EligibilityResult
    lane: Lane | None = None  # where it is on the user's board, if anywhere


class ApplicationIn(BaseModel):
    event_id: int
    lane: Lane


class ApplicationOut(ApplicationIn):
    id: int
    event_name: str
    updated_at: datetime


class AgentActionOut(BaseModel):
    id: int
    created_at: datetime
    kind: str
    summary: str
    reason: str | None
    source_ref: str | None
    autonomy: str


class CreatedUser(BaseModel):
    id: int


class RunSummaryOut(BaseModel):
    pages_read: int
    pages_skipped: int
    llm_calls: int
    events_saved: int
    input_tokens: int
    output_tokens: int
    errors: list[str]
