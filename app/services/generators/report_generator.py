from __future__ import annotations

from app.services.analyzers.paper_analyzer import PaperAnalysisResult
from app.services.analyzers.research_gap_finder import ResearchGapResult
from app.services.analyzers.trend_analyzer import TrendAnalysisResult
from app.services.collectors.base import CollectedPaper


class ReportGenerator:
    def generate(
        self,
        *,
        topic: str,
        papers: list[CollectedPaper],
        analyses: list[PaperAnalysisResult],
        trends: TrendAnalysisResult,
        gaps: ResearchGapResult,
    ) -> str:
        sections = [
            ("## 一、研究概览", self._render_overview(topic, papers)),
            ("## 二、重点论文解读", self._render_analyses(papers, analyses)),
            ("## 三、研究趋势分析", self._render_trends(trends)),
            ("## 四、新兴研究方向", self._render_emerging_directions(trends, gaps)),
            ("## 五、研究机会与空白", self._render_gaps(gaps)),
            ("## 六、推荐阅读", self._render_recommended_reading(papers)),
        ]
        return "\n\n".join(["# 研究报告", *[f"{title}\n{body}" for title, body in sections]])

    def _render_overview(self, topic: str, papers: list[CollectedPaper]) -> str:
        return f"主题：{topic}\n论文数量：{len(papers)}"

    def _render_analyses(
        self,
        papers: list[CollectedPaper],
        analyses: list[PaperAnalysisResult],
    ) -> str:
        if not analyses:
            return "暂无单篇分析结果。"
        lines: list[str] = []
        for index, analysis in enumerate(analyses, start=1):
            title = self._resolve_analysis_title(papers, index - 1)
            lines.append(
                f"{index}. {title} | 问题：{analysis.problem or '暂无'} | 方法：{analysis.method or '暂无'} | "
                f"创新：{analysis.innovation or '暂无'} | 结果：{analysis.results or '暂无'} | 局限：{analysis.limitations or '暂无'} | "
                f"研究空白：{analysis.research_gap or '暂无'} | 研究机会：{analysis.research_opportunity or '暂无'}"
            )
        return "\n".join(lines)

    def _render_emerging_directions(
        self,
        trends: TrendAnalysisResult,
        gaps: ResearchGapResult,
    ) -> str:
        topics = trends.hot_topics[:3]
        if topics:
            lines = [f"{index}. {topic}" for index, topic in enumerate(topics, start=1)]
            if gaps.summary:
                lines.append(f"方向判断：{gaps.summary}")
            return "\n".join(lines)
        if gaps.summary:
            return f"暂无明确热点方向，可优先关注：{gaps.summary}"
        return "暂无新兴研究方向。"

    def _render_trends(self, trends: TrendAnalysisResult) -> str:
        keywords = "、".join(trends.hot_keywords) if trends.hot_keywords else "暂无"
        topics = "、".join(trends.hot_topics) if trends.hot_topics else "暂无"
        signals = (
            "；".join(f"{item['year']} 年 {item['count']} 篇" for item in trends.growth_signals)
            if trends.growth_signals
            else "暂无"
        )
        return f"热点关键词：{keywords}\n热点主题：{topics}\n增长信号：{signals}\n总结：{trends.summary or '暂无趋势总结。'}"

    def _render_gaps(self, gaps: ResearchGapResult) -> str:
        if not gaps.gaps:
            return f"总结：{gaps.summary or '暂无研究空白结论。'}"
        details = "\n".join(
            f"{index}. {gap.title}：{gap.description}；机会：{gap.opportunity}"
            for index, gap in enumerate(gaps.gaps, start=1)
        )
        return f"{details}\n总结：{gaps.summary or '暂无研究空白结论。'}"

    def _render_recommended_reading(self, papers: list[CollectedPaper]) -> str:
        if not papers:
            return "暂无推荐阅读。"
        return "\n".join(
            f"{index}. {self._format_paper_title(paper)} | {paper.venue} {paper.year} | {paper.url}"
            for index, paper in enumerate(papers[:5], start=1)
        )

    def _resolve_analysis_title(self, papers: list[CollectedPaper], index: int) -> str:
        if 0 <= index < len(papers):
            return self._format_paper_title(papers[index])
        return "未匹配论文"

    def _format_paper_title(self, paper: CollectedPaper) -> str:
        title = paper.title.strip() or "未命名论文"
        title_zh = paper.title_zh.strip()
        if title_zh:
            return f"{title}（{title_zh}）"
        return title
