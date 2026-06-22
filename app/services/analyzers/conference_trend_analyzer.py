from __future__ import annotations

from dataclasses import dataclass

from app.services.collectors.base import CollectedPaper
from app.services.llm.prompts import build_conference_trend_prompt
from app.services.llm.schemas import CONFERENCE_TREND_SCHEMA


@dataclass(slots=True)
class ConferenceTrendAnalysisResult:
    summary: str
    hot_methods: list[str]
    hot_applications: list[str]
    emerging_signals: list[str]


class ConferenceTrendAnalyzer:
    def __init__(self, llm_client) -> None:
        self._llm_client = llm_client

    def analyze(self, *, conference: str, year: int, papers: list[CollectedPaper]) -> ConferenceTrendAnalysisResult:
        payload = self._llm_client.generate_structured(
            prompt=build_conference_trend_prompt(conference=conference, year=year, papers=papers),
            schema=CONFERENCE_TREND_SCHEMA,
        )
        if not isinstance(payload, dict):
            return ConferenceTrendAnalysisResult("", [], [], [])
        return ConferenceTrendAnalysisResult(
            summary=self._normalize_text(payload.get("summary")),
            hot_methods=self._normalize_list(payload.get("hot_methods")),
            hot_applications=self._normalize_list(payload.get("hot_applications")),
            emerging_signals=self._normalize_list(payload.get("emerging_signals")),
        )

    def _normalize_text(self, value: object) -> str:
        return value.strip() if isinstance(value, str) else ""

    def _normalize_list(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        result: list[str] = []
        for item in value:
            text = self._normalize_text(item)
            if text:
                result.append(text)
        return result
