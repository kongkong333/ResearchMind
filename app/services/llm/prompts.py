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


def build_conference_trend_prompt(*, conference: str, year: int, papers: list[CollectedPaper]) -> str:
    titles = "\n".join(f"{index}. {paper.title}" for index, paper in enumerate(papers, start=1)) or "暂无标题"
    return (
        f"请基于以下 {conference.upper()} {year} accepted 论文标题，提炼会议热点趋势。\n"
        "你必须严格依据论文标题本身进行分析，严禁根据常识、经验或领域背景补充标题中未明确出现的信息。\n"
        "严禁杜撰或联想以下内容：论文摘要、实验结果、性能提升、作者动机、数据集细节、模型结构细节、训练流程细节、与往年对比、未来影响。\n"
        "如果标题证据不足，请只做高层、保守、可从标题直接支持的归纳；宁可少说，也不要猜测。\n"
        "请严格按照以下 4 个模块组织内容，并确保各模块之间不要重复。\n"
        "summary：输出 2-4 句中文总结，只概括从标题中反复出现的方法关键词、任务关键词和整体主题，不要编号，不要写成论文列表，不要写标题中没有出现的技术结论。\n"
        "hot_methods：最多输出 10 条。每条先写一个方法方向名，再用一句短解释说明它是如何从标题中体现出来的。只能依据标题中的显式术语、范式名称或方法关键词归纳，不得补充未出现的实现细节。\n"
        "hot_applications：最多输出 10 条。每条先写一个应用场景、任务方向或问题域，再用一句短解释说明它是如何从标题中体现出来的。不要把方法名称改写成应用，也不要扩展成标题未写出的实际落地场景。\n"
        "emerging_signals：最多输出 10 条。每条写一个值得关注的新信号，再用一句短解释说明它具体对应了哪些标题中的新术语、组合或方向。只有当标题本身能支持这个信号时才能输出。\n"
        "如果某一类高置信方向不足，就少写；不要为了凑到 10 条而编造不存在的细节、结果或趋势。\n"
        "所有内容请使用中文输出，表达尽量简洁、克制、信息密度高。\n"
        "标题列表：\n"
        f"{titles}\n"
        "请输出结构化结果。"
    )
