from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


RunStatus = Literal["pending", "running", "completed", "failed"]
StageStatus = Literal["pending", "running", "completed", "failed"]
DatabaseName = Literal["pubmed", "arxiv"]


class ResearchRunCreate(BaseModel):
    topic: str = Field(min_length=2)
    database: DatabaseName = "pubmed"
    start_date: date | None = None
    end_date: date | None = None
    max_results: int = Field(default=5, ge=1, le=20)
    venues: list[str] = Field(default_factory=list)
    openai_api_key: str | None = None
    openai_model: str | None = None
    openai_base_url: str | None = None


class StageStateRead(BaseModel):
    stage_key: str
    stage_label: str
    status: StageStatus = "pending"
    message: str = ""
    current: int = 0
    total: int = 0


class ResearchRunStatusRead(BaseModel):
    run_id: str
    topic: str
    status: RunStatus
    current_message: str = ""
    stages: list[StageStateRead] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    latest_report_path: str | None = None
    report_artifact_path: str | None = None


class ResearchRunRead(BaseModel):
    id: int
    topic: str
    status: str
    paper_count: int = 0
    start_date: date | None = None
    end_date: date | None = None
    error_message: str | None = None
