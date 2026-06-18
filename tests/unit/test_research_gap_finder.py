from app.services.collectors.base import CollectedPaper
from app.services.analyzers.paper_analyzer import PaperAnalysisResult
from app.services.analyzers.research_gap_finder import ResearchGapFinder


def test_research_gap_finder_aggregates_from_per_paper_analysis() -> None:
    finder = ResearchGapFinder()

    result = finder.find_gaps(
        papers=[
            CollectedPaper(
                source_id="1",
                title="Paper",
                authors=["Ada"],
                abstract="Abstract",
                year=2026,
                venue="ICML",
                url="https://example.com/1",
                keywords=["agent"],
            )
        ],
        analyses=[
            PaperAnalysisResult(
                problem="问题",
                method="方法",
                innovation="创新",
                results="结果",
                limitations="大多只在离线基准测试",
                research_gap="真实环境验证不足",
                research_opportunity="构建真实工作流评测",
            )
        ],
    )

    assert "真实工作流评测" in result.summary
    assert result.gaps[0].title == "Paper"
    assert result.gaps[0].opportunity == "构建真实工作流评测"


def test_research_gap_finder_returns_empty_summary_when_no_analysis() -> None:
    finder = ResearchGapFinder()

    result = finder.find_gaps(papers=[], analyses=[])

    assert result.gaps == []
    assert result.summary == "暂无研究空白结论。"
