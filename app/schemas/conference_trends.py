from __future__ import annotations

from pydantic import BaseModel, Field


class ConferenceTrendRunCreate(BaseModel):
    conference: str = Field(min_length=2)
    year: int = Field(ge=2013, le=2100)
    limit: int = Field(default=100, ge=1, le=2000)
    tracks: list[str] = Field(default_factory=list)
    openai_api_key: str | None = None
    openai_model: str | None = None
    openai_base_url: str | None = None


class ConferenceTrackListRequest(BaseModel):
    conference: str = Field(min_length=2)
    year: int = Field(ge=2013, le=2100)
