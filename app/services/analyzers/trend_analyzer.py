from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from app.services.collectors.base import CollectedPaper


@dataclass(slots=True, eq=True)
class TrendAnalysisResult:
    hot_keywords: list[str]
    hot_topics: list[str]
    growth_signals: list[dict[str, int]]
    summary: str


class TrendAnalyzer:
    def analyze(self, papers: list[CollectedPaper]) -> TrendAnalysisResult:
        if not papers:
            return TrendAnalysisResult(
                hot_keywords=[],
                hot_topics=[],
                growth_signals=[],
                summary="暂无可分析的趋势数据。",
            )

        keyword_counts = Counter()
        topic_counts = Counter()
        year_counts = Counter()

        for paper in sorted(papers, key=lambda item: (item.year, item.source_id)):
            keyword_counts.update(self._normalize_keywords(paper.keywords))
            topic_counts.update(self._extract_topics(paper))
            year_counts.update([paper.year])

        hot_keywords = [item for item, _ in sorted(keyword_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]]
        hot_topics = [item for item, _ in sorted(topic_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]]
        growth_signals = [
            {"year": year, "count": year_counts[year]}
            for year in sorted(year_counts)
        ]
        summary = (
            f"共分析 {len(papers)} 篇论文，"
            f"高频关键词包括 {', '.join(hot_keywords) if hot_keywords else '暂无'}，"
            f"近年产出主要集中在 {growth_signals[-1]['year']}。"
        )
        return TrendAnalysisResult(hot_keywords, hot_topics, growth_signals, summary)

    def _extract_topics(self, paper: CollectedPaper) -> list[str]:
        title = paper.title.strip()
        if not title:
            return []
        lowered = title.lower()
        if "agent" in lowered and "planning" in lowered:
            return ["Agent Planning"]
        if "agent" in lowered and "memory" in lowered:
            return ["Agent Memory"]
        return [title]

    def _normalize_keywords(self, keywords: list[object]) -> list[str]:
        normalized: list[str] = []
        for keyword in keywords:
            if not isinstance(keyword, str):
                continue
            cleaned = keyword.strip().lower()
            if cleaned:
                normalized.append(cleaned)
        return normalized
