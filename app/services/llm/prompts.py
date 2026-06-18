from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.collectors.base import CollectedPaper

if TYPE_CHECKING:
    from app.services.analyzers.paper_analyzer import PaperAnalysisResult


def build_paper_analysis_prompt(paper: CollectedPaper) -> str:
    return (
        "请用中文提炼以下论文的 summary、problem、method、innovation、results、limitations、research_gap、research_opportunity。\n"
        "其中 summary 需写成 1-2句归纳，概括论文做了什么、如何做、效果如何；其余字段保持简洁。\n"
        f"标题：{paper.title}\n摘要：{paper.abstract}\n关键词：{', '.join(paper.keywords)}"
    )


def build_research_gap_prompt(
    papers: list[CollectedPaper],
    analyses: list["PaperAnalysisResult"],
) -> str:
    titles = "；".join(paper.title for paper in papers) or "暂无论文"
    limits = "；".join(analysis.limitations for analysis in analyses if analysis.limitations) or "暂无局限信息"
    return f"请基于论文与局限总结研究空白。论文：{titles}。局限：{limits}。"
