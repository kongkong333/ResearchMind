from __future__ import annotations

from app.services.analyzers.paper_analyzer import PaperAnalysisResult, PaperAnalyzer
from app.services.analyzers.research_gap_finder import ResearchGapFinder, ResearchGapItem, ResearchGapResult
from app.services.analyzers.trend_analyzer import TrendAnalyzer, TrendAnalysisResult
from app.services.collectors.arxiv_source import ArxivPaperSource
from app.services.collectors.base import CollectedPaper
from app.services.collectors.paper_collector import PaperCollector
from app.services.collectors.pubmed_source import PubMedPaperSource
from app.services.generators.report_generator import ReportGenerator
from app.workflows.progress import ProgressEvent
from app.workflows.state import ResearchState


STAGE_LABELS = {
    "collect_papers": "抓取论文",
    "analyze_papers": "分析论文",
    "generate_report": "生成报告",
}


def _emit_progress(
    progress_callback,
    *,
    stage_key: str,
    status: str,
    message: str,
    current: int = 0,
    total: int = 0,
) -> None:
    if progress_callback is None:
        return
    progress_callback(
        ProgressEvent(
            stage_key=stage_key,
            stage_label=STAGE_LABELS[stage_key],
            status=status,
            message=message,
            current=current,
            total=total,
        )
    )


def collect_papers(
    state: ResearchState,
    *,
    paper_collector: PaperCollector | None = None,
    source_papers: list[CollectedPaper] | None = None,
    paper_source: object | None = None,
    progress_callback=None,
) -> ResearchState:
    _emit_progress(
        progress_callback,
        stage_key="collect_papers",
        status="running",
        message="正在抓取论文",
    )
    collector = paper_collector or PaperCollector()
    papers = source_papers
    if papers is None:
        try:
            active_source = paper_source or _paper_source_for_database(
                state.database,
                limit=state.max_results,
            )
            papers = active_source.fetch(
                state.topic,
                start_date=state.date_range[0],
                end_date=state.date_range[1],
                limit=state.max_results,
            )
        except Exception as exc:  # pragma: no cover
            state.errors.append(f"{state.database}_fetch_failed: {exc}")
            papers = []
    state.papers = collector.collect_from_papers(papers, topic=state.topic, venues=state.venues)
    _emit_progress(
        progress_callback,
        stage_key="collect_papers",
        status="completed",
        message=f"已抓取并筛选 {len(state.papers)} 篇论文",
        current=len(state.papers),
        total=len(state.papers),
    )
    return state


def _paper_source_for_database(database: str, *, limit: int) -> object:
    normalized = (database or "pubmed").strip().lower()
    source_map = {
        "pubmed": PubMedPaperSource,
        "arxiv": ArxivPaperSource,
    }
    source_cls = source_map.get(normalized, PubMedPaperSource)
    return source_cls(limit=limit)


def analyze_papers(
    state: ResearchState,
    *,
    analyzer: PaperAnalyzer | None = None,
    llm_client=None,
    progress_callback=None,
) -> ResearchState:
    if analyzer is not None:
        paper_analyzer = analyzer
    elif llm_client is not None:
        paper_analyzer = PaperAnalyzer(llm_client)
    else:
        raise ValueError("LLM client is required for paper analysis.")
    analyses: list[dict[str, str]] = []
    papers = state.papers[: state.max_results]
    total = len(papers)
    start_message = "未找到可分析论文" if total == 0 else "正在分析论文 0/{0}".format(total)
    _emit_progress(
        progress_callback,
        stage_key="analyze_papers",
        status="running",
        message=start_message,
        current=0,
        total=total,
    )
    for index, paper in enumerate(papers, start=1):
        result = paper_analyzer.analyze(paper)
        analyses.append(_paper_analysis_to_dict(result))
        _emit_progress(
            progress_callback,
            stage_key="analyze_papers",
            status="running",
            message=f"正在分析论文 {index}/{total}",
            current=index,
            total=total,
        )
    state.paper_analyses = analyses
    completed_message = "分析完成" if total else "未找到可分析论文"
    _emit_progress(
        progress_callback,
        stage_key="analyze_papers",
        status="completed",
        message=completed_message,
        current=total,
        total=total,
    )
    return state


def run_trend_analysis(
    state: ResearchState,
    *,
    analyzer: TrendAnalyzer | None = None,
    progress_callback=None,
) -> ResearchState:
    _emit_progress(
        progress_callback,
        stage_key="run_trend_analysis",
        status="running",
        message="正在统计趋势",
    )
    trend_analyzer = analyzer or TrendAnalyzer()
    result = trend_analyzer.analyze(state.papers)
    state.trend_snapshot = {
        "hot_keywords": result.hot_keywords,
        "hot_topics": result.hot_topics,
        "growth_signals": result.growth_signals,
        "summary": result.summary,
    }
    _emit_progress(
        progress_callback,
        stage_key="run_trend_analysis",
        status="completed",
        message="趋势统计完成",
    )
    return state


def find_research_gaps(
    state: ResearchState,
    *,
    finder: ResearchGapFinder | None = None,
    progress_callback=None,
) -> ResearchState:
    _emit_progress(
        progress_callback,
        stage_key="find_research_gaps",
        status="running",
        message="正在整理研究机会",
    )
    gap_finder = finder or ResearchGapFinder()
    analyses = [_dict_to_paper_analysis(item) for item in state.paper_analyses]
    result = gap_finder.find_gaps(state.papers, analyses)
    state.research_gaps = {
        "gaps": [
            {
                "title": gap.title,
                "description": gap.description,
                "opportunity": gap.opportunity,
            }
            for gap in result.gaps
        ],
        "summary": result.summary,
    }
    _emit_progress(
        progress_callback,
        stage_key="find_research_gaps",
        status="completed",
        message="研究机会整理完成",
    )
    return state


def generate_report(
    state: ResearchState,
    *,
    generator: ReportGenerator | None = None,
    progress_callback=None,
) -> ResearchState:
    _emit_progress(
        progress_callback,
        stage_key="generate_report",
        status="running",
        message="正在生成最终报告",
    )
    report_generator = generator or ReportGenerator()
    analyses = [_dict_to_paper_analysis(item) for item in state.paper_analyses]
    state.report_markdown = report_generator.generate(
        topic=state.topic,
        papers=state.papers,
        analyses=analyses,
    )
    _emit_progress(
        progress_callback,
        stage_key="generate_report",
        status="completed",
        message="报告生成完成",
    )
    return state


def _paper_analysis_to_dict(result: PaperAnalysisResult) -> dict[str, str]:
    return {
        "summary": result.summary,
        "problem": result.problem,
        "method": result.method,
        "innovation": result.innovation,
        "results": result.results,
        "limitations": result.limitations,
        "research_gap": result.research_gap,
        "research_opportunity": result.research_opportunity,
    }


def _dict_to_paper_analysis(item: dict[str, str] | None) -> PaperAnalysisResult:
    payload = item or {}
    return PaperAnalysisResult(
        summary=str(payload.get("summary", "")),
        problem=str(payload.get("problem", "")),
        method=str(payload.get("method", "")),
        innovation=str(payload.get("innovation", "")),
        results=str(payload.get("results", "")),
        limitations=str(payload.get("limitations", "")),
        research_gap=str(payload.get("research_gap", "")),
        research_opportunity=str(payload.get("research_opportunity", "")),
    )


def _dict_to_trend_result(item: dict[str, object] | None) -> TrendAnalysisResult:
    payload = item or {}
    return TrendAnalysisResult(
        hot_keywords=list(payload.get("hot_keywords", [])),
        hot_topics=list(payload.get("hot_topics", [])),
        growth_signals=list(payload.get("growth_signals", [])),
        summary=str(payload.get("summary", "")),
    )


def _dict_to_gap_result(item: dict[str, object] | None) -> ResearchGapResult:
    payload = item or {}
    gaps = payload.get("gaps", [])
    normalized_gaps: list[ResearchGapItem] = []
    for gap in gaps if isinstance(gaps, list) else []:
        if not isinstance(gap, dict):
            continue
        normalized_gaps.append(
            ResearchGapItem(
                title=str(gap.get("title", "")),
                description=str(gap.get("description", "")),
                opportunity=str(gap.get("opportunity", "")),
            )
        )
    return ResearchGapResult(
        gaps=normalized_gaps,
        summary=str(payload.get("summary", "")),
    )
