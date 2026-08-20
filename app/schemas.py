from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=80)
    assignee: str = Field(..., min_length=1)
    priority: str = "medium"

    @field_validator("title", "assignee")
    @classmethod
    def strip_nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("empty")
        return value

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"low", "medium", "high"}:
            raise ValueError("invalid priority")
        return value


class NoteCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=500)

    @field_validator("body")
    @classmethod
    def strip_nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("empty")
        return value


class NoteOut(BaseModel):
    id: int
    ticket_id: int
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketOut(BaseModel):
    id: int
    title: str
    assignee: str
    priority: str
    status: str
    created_at: datetime
    notes: Optional[list[NoteOut]] = None

    model_config = {"from_attributes": True}


class ErrorOut(BaseModel):
    error: str


class HealthOut(BaseModel):
    ok: bool
    db: str
