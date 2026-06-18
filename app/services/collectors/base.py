from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(slots=True)
class CollectedPaper:
    source_id: str
    title: str
    authors: list[str]
    abstract: str
    year: int
    venue: str
    url: str
    pdf_url: str = ""
    keywords: list[str] = field(default_factory=list)
    source: str = "unknown"
    published_at: date | None = None
    title_zh: str = ""
    abstract_zh: str = ""
