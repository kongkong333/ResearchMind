from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.collectors.base import CollectedPaper

if TYPE_CHECKING:
    from app.services.analyzers.paper_analyzer import PaperAnalysisResult


def build_paper_analysis_prompt(paper: CollectedPaper) -> str:
    return (
        "请用中文提炼以下论文的 summary、problem、method、innovation、results、limitations、research_gap、research_opportunity。\n"
        "其中 summary 需写成 2-3句归纳，概括论文针对什么问题、做了什么、如何做、效果如何。\n"
        "research_opportunity 需要你发散思维分析，其余你只能基于下面提供的标题、摘要、关键词和发表信息据实分析。\n"
        "如果摘要没有明确给出局限性、实验细节或创新点等信息，请直接说明摘要未明确说明，不要补充猜测。\n"
        f"标题：{paper.title}\n"
        f"摘要：{paper.abstract}\n"
        f"关键词：{', '.join(paper.keywords)}\n"
        f"来源：{paper.source}\n"
        f"发表信息：{paper.venue} {paper.year}"
    )


def build_research_gap_prompt(
    papers: list[CollectedPaper],
    analyses: list["PaperAnalysisResult"],
) -> str:
    titles = "；".join(paper.title for paper in papers) or "暂无论文"
    limits = "；".join(analysis.limitations for analysis in analyses if analysis.limitations) or "暂无局限信息"
    return f"请基于论文与局限总结研究空白。论文：{titles}。局限：{limits}。"
