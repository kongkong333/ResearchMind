from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PaperRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: str
    title: str
    authors: list[str]
    abstract: str
    year: int
    venue: str
    url: str
    keywords: list[str]
    published_at: date | None = None
    created_at: datetime | None = None
