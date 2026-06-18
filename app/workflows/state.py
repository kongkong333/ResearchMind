from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from uuid import uuid4

from app.services.collectors.base import CollectedPaper


@dataclass(slots=True)
class ResearchState:
    topic: str
    run_id: str = field(default_factory=lambda: str(uuid4()))
    date_range: tuple[date | None, date | None] = (None, None)
    max_results: int = 5
    venues: list[str] = field(default_factory=list)
    papers: list[CollectedPaper] = field(default_factory=list)
    paper_analyses: list[dict[str, str]] = field(default_factory=list)
    trend_snapshot: dict[str, object] | None = None
    research_gaps: dict[str, object] | None = None
    report_markdown: str = ""
    errors: list[str] = field(default_factory=list)
