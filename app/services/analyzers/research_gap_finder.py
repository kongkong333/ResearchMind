from __future__ import annotations

from dataclasses import dataclass

from app.services.analyzers.paper_analyzer import PaperAnalysisResult
from app.services.collectors.base import CollectedPaper


@dataclass(slots=True, eq=True)
class ResearchGapItem:
    title: str
    description: str
    opportunity: str


@dataclass(slots=True, eq=True)
class ResearchGapResult:
    gaps: list[ResearchGapItem]
    summary: str


class ResearchGapFinder:
    def find_gaps(
        self,
        papers: list[CollectedPaper],
        analyses: list[PaperAnalysisResult],
    ) -> ResearchGapResult:
        items: list[ResearchGapItem] = []
        for index, analysis in enumerate(analyses):
            gap = analysis.research_gap.strip()
            opportunity = analysis.research_opportunity.strip()
            description = analysis.limitations.strip() or gap or "暂无明显研究空白"
            if not gap and not opportunity and not description:
                continue
            title = papers[index].title if index < len(papers) else f"论文 {index + 1}"
            items.append(
                ResearchGapItem(
                    title=title,
                    description=description,
                    opportunity=opportunity or "暂无明确研究机会",
                )
            )
        summary = self._build_summary(items)
        return ResearchGapResult(gaps=items, summary=summary)

    def _build_summary(self, items: list[ResearchGapItem]) -> str:
        if not items:
            return "暂无研究空白结论。"
        top_descriptions = "；".join(item.description for item in items[:3] if item.description)
        top_opportunities = "；".join(item.opportunity for item in items[:3] if item.opportunity)
        return f"主要空白：{top_descriptions or '暂无'}。潜在机会：{top_opportunities or '暂无'}。"
