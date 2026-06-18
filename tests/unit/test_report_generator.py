from app.services.analyzers.paper_analyzer import PaperAnalysisResult
from app.services.analyzers.research_gap_finder import ResearchGapResult, ResearchGapItem
from app.services.analyzers.trend_analyzer import TrendAnalysisResult
from app.services.collectors.base import CollectedPaper
from app.services.generators.report_generator import ReportGenerator


def test_report_generator_outputs_six_chinese_sections() -> None:
    generator = ReportGenerator()

    report = generator.generate(
        topic="AI Agent",
        papers=[
            CollectedPaper(
                source_id="1",
                title="Agent Planning",
                authors=["Ada"],
                abstract="Abstract",
                year=2026,
                venue="ICML",
                url="https://example.com/1",
                keywords=["agent", "planning"],
            )
        ],
        analyses=[
            PaperAnalysisResult(
                problem="问题",
                method="方法",
                innovation="创新",
                results="结果",
                limitations="局限",
                research_gap="研究空白",
                research_opportunity="研究机会",
            )
        ],
        trends=TrendAnalysisResult(
            hot_keywords=["agent"],
            hot_topics=["Agent Planning"],
            growth_signals=[{"year": 2026, "count": 1}],
            summary="agent 方向升温",
        ),
        gaps=ResearchGapResult(
            gaps=[
                ResearchGapItem(
                    title="真实场景不足",
                    description="缺少线上验证",
                    opportunity="做长期部署研究",
                )
            ],
            summary="落地验证仍不足",
        ),
    )

    for heading in [
        "# 研究报告",
        "## 一、研究概览",
        "## 二、重点论文解读",
        "## 三、研究趋势分析",
        "## 四、新兴研究方向",
        "## 五、研究机会与空白",
        "## 六、推荐阅读",
    ]:
        assert heading in report


def test_report_generator_handles_empty_inputs_without_crashing() -> None:
    generator = ReportGenerator()

    report = generator.generate(
        topic="AI Agent",
        papers=[],
        analyses=[],
        trends=TrendAnalysisResult(
            hot_keywords=[],
            hot_topics=[],
            growth_signals=[],
            summary="暂无趋势数据",
        ),
        gaps=ResearchGapResult(gaps=[], summary="暂无研究空白结论"),
    )

    assert "# 研究报告" in report
    assert "## 一、研究概览" in report
    assert "## 六、推荐阅读" in report
    assert "暂无" in report


def test_report_generator_handles_mismatched_paper_and_analysis_lengths() -> None:
    generator = ReportGenerator()

    report = generator.generate(
        topic="AI Agent",
        papers=[
            CollectedPaper(
                source_id="1",
                title="Only Paper",
                authors=["Ada"],
                abstract="Abstract",
                year=2026,
                venue="ICML",
                url="https://example.com/1",
                keywords=["agent"],
            )
        ],
        analyses=[
            PaperAnalysisResult(problem="问题1"),
            PaperAnalysisResult(problem="问题2"),
        ],
        trends=TrendAnalysisResult(
            hot_keywords=[],
            hot_topics=[],
            growth_signals=[],
            summary="暂无趋势数据",
        ),
        gaps=ResearchGapResult(gaps=[], summary="暂无研究空白结论"),
    )

    assert "1. Only Paper | 问题：问题1" in report
    assert "2. 未匹配论文 | 问题：问题2" in report
    assert "研究机会" in report or "暂无" in report


def test_report_generator_includes_bilingual_titles_when_available() -> None:
    generator = ReportGenerator()

    report = generator.generate(
        topic="AI Agent",
        papers=[
            CollectedPaper(
                source_id="1",
                title="Agent Planning",
                title_zh="智能体规划",
                authors=["Ada"],
                abstract="Abstract",
                year=2026,
                venue="ICML",
                url="https://example.com/1",
                keywords=["agent", "planning"],
            )
        ],
        analyses=[PaperAnalysisResult(problem="问题")],
        trends=TrendAnalysisResult(
            hot_keywords=[],
            hot_topics=[],
            growth_signals=[],
            summary="暂无趋势数据",
        ),
        gaps=ResearchGapResult(gaps=[], summary="暂无研究空白结论"),
    )

    assert "Agent Planning（智能体规划）" in report
