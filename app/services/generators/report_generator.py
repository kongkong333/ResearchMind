from __future__ import annotations

from app.services.analyzers.paper_analyzer import PaperAnalysisResult
from app.services.collectors.base import CollectedPaper


class ReportGenerator:
    def generate(
        self,
        *,
        topic: str,
        papers: list[CollectedPaper],
        analyses: list[PaperAnalysisResult],
    ) -> str:
        sections = [
            ("## 一、研究概览", self._render_overview(topic, papers)),
            ("## 二、重点论文解读", self._render_analyses(papers, analyses)),
            ("## 三、研究机会", self._render_opportunities(analyses)),
            ("## 四、推荐阅读", self._render_recommended_reading(papers)),
        ]
        return "\n\n".join(["# 研究报告", *[f"{title}\n{body}" for title, body in sections]])

    def _render_overview(self, topic: str, papers: list[CollectedPaper]) -> str:
        if not papers:
            return f"主题：{topic}\n论文数量：0"
        lines = [
            f"主题：{topic}",
            f"论文数量：{len(papers)}",
            "分析引用可用性：",
        ]
        for index, paper in enumerate(papers, start=1):
            lines.append(
                f"{index}. {paper.title.strip() or '未命名论文'} | PDF：{'有' if paper.pdf_url.strip() else '无'}"
            )
        return "\n".join(lines)

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
            lines.append("\n".join([
                f"{index}. {title}",
                f"简要概述：{analysis.summary or self._resolve_analysis_summary(papers, index - 1)}",
                f"针对的问题：{analysis.problem or '暂无'}",
                f"方法：{analysis.method or '暂无'}",
                f"创新点：{analysis.innovation or '暂无'}",
                f"结果：{analysis.results or '暂无'}",
                f"局限：{analysis.limitations or '暂无'}",
            ]))
        return "\n\n".join(lines)

    def _render_opportunities(self, analyses: list[PaperAnalysisResult]) -> str:
        opportunities = [item.research_opportunity.strip() for item in analyses if item.research_opportunity.strip()]
        gaps = [item.research_gap.strip() for item in analyses if item.research_gap.strip()]
        limitations = [item.limitations.strip() for item in analyses if item.limitations.strip()]

        opportunity_lines = opportunities or ["暂无明确可复用机会。"]
        gap_lines = gaps + [item for item in limitations if item not in gaps]
        gap_lines = gap_lines or ["暂无明确待改进问题。"]

        return "\n".join([
            "1. 这些论文可利用/结合之处（如模型结构、方法论、技术路线等）",
            *[f"- {line}" for line in opportunity_lines],
            "2. 这些论文尚未做好的地方",
            *[f"- {line}" for line in gap_lines],
        ])

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

    def _resolve_analysis_summary(self, papers: list[CollectedPaper], index: int) -> str:
        if 0 <= index < len(papers):
            abstract = papers[index].abstract_zh.strip() or papers[index].abstract.strip()
            return abstract or "暂无"
        return "暂无"

    def _format_paper_title(self, paper: CollectedPaper) -> str:
        title = paper.title.strip() or "未命名论文"
        title_zh = paper.title_zh.strip()
        if title_zh:
            return f"{title}（{title_zh}）"
        return title
