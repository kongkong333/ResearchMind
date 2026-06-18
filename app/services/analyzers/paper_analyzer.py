from __future__ import annotations

from dataclasses import dataclass

from app.services.collectors.base import CollectedPaper
from app.services.llm.prompts import build_paper_analysis_prompt
from app.services.llm.schemas import PAPER_ANALYSIS_SCHEMA


@dataclass(slots=True)
class PaperAnalysisResult:
    problem: str = ""
    method: str = ""
    innovation: str = ""
    results: str = ""
    limitations: str = ""
    research_gap: str = ""
    research_opportunity: str = ""


class PaperAnalyzer:
    def __init__(self, llm_client) -> None:
        self._llm_client = llm_client

    def analyze(self, paper: CollectedPaper) -> PaperAnalysisResult:
        payload = self._llm_client.generate_structured(
            prompt=build_paper_analysis_prompt(paper),
            schema=PAPER_ANALYSIS_SCHEMA,
        )
        if not isinstance(payload, dict):
            return PaperAnalysisResult()
        return PaperAnalysisResult(
            problem=self._normalize_text(payload.get("problem")),
            method=self._normalize_text(payload.get("method")),
            innovation=self._normalize_text(payload.get("innovation")),
            results=self._normalize_text(payload.get("results")),
            limitations=self._normalize_text(payload.get("limitations")),
            research_gap=self._normalize_text(payload.get("research_gap")),
            research_opportunity=self._normalize_text(payload.get("research_opportunity")),
        )

    def _normalize_text(self, value: object) -> str:
        return value.strip() if isinstance(value, str) else ""
