from app.services.collectors.base import CollectedPaper
from app.services.analyzers.trend_analyzer import TrendAnalyzer


def test_trend_analyzer_is_deterministic_and_summarizes_growth() -> None:
    analyzer = TrendAnalyzer()
    papers = [
        CollectedPaper(
            source_id="1",
            title="Agent Planning with Tools",
            authors=["Ada"],
            abstract="Tool use and planning",
            year=2026,
            venue="ICML",
            url="https://example.com/1",
            keywords=["agent", "planning", "tools"],
        ),
        CollectedPaper(
            source_id="2",
            title="Agent Memory for Planning",
            authors=["Grace"],
            abstract="Memory improves planning",
            year=2026,
            venue="NeurIPS",
            url="https://example.com/2",
            keywords=["agent", "memory", "planning"],
        ),
        CollectedPaper(
            source_id="3",
            title="RAG Agents",
            authors=["Linus"],
            abstract="Agent retrieval system",
            year=2025,
            venue="ICLR",
            url="https://example.com/3",
            keywords=["agent", "retrieval"],
        ),
    ]

    first = analyzer.analyze(papers)
    second = analyzer.analyze(list(reversed(papers)))

    assert first == second
    assert first.hot_keywords[0] == "agent"
    assert any(signal["year"] == 2026 for signal in first.growth_signals)
    assert first.summary


def test_trend_analyzer_handles_empty_input() -> None:
    analyzer = TrendAnalyzer()

    result = analyzer.analyze([])

    assert result.hot_keywords == []
    assert result.hot_topics == []
    assert result.summary


def test_trend_analyzer_ignores_invalid_keywords() -> None:
    analyzer = TrendAnalyzer()

    result = analyzer.analyze(
        [
            CollectedPaper(
                source_id="4",
                title="Agent Memory",
                authors=["Ada"],
                abstract="Abstract",
                year=2026,
                venue="ICLR",
                url="https://example.com/4",
                keywords=["agent", None, 123, "  memory  ", ""],
            )
        ]
    )

    assert result.hot_keywords == ["agent", "memory"]
