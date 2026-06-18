from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field


DEFAULT_VENUES = ["ICLR", "NeurIPS", "ICML", "AAAI"]


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    app_name: str = "ResearchMind"
    database_url: str = Field(alias="DATABASE_URL")
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    default_venues: list[str] = Field(default_factory=lambda: DEFAULT_VENUES.copy())
    report_output_dir: str = "reports"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.environ.get("DATABASE_URL", ""),
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        openai_model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
        openai_base_url=os.environ.get("OPENAI_BASE_URL") or None,
    )
