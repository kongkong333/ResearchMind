from app.services.collectors.paper_collector import PaperCollector
from app.services.collectors.base import CollectedPaper


def test_paper_collector_filters_by_venue_and_deduplicates_without_topic_filtering() -> None:
    collector = PaperCollector()
    papers = [
        CollectedPaper(
            source_id="1",
            title="Large Language Agents for Planning",
            authors=["Ada"],
            abstract="Agent planning with tools",
            year=2026,
            venue="ICML",
            url="https://example.com/1",
            keywords=["agents", "planning"],
        ),
        CollectedPaper(
            source_id="1",
            title="Duplicate record",
            authors=["Ada"],
            abstract="Duplicate",
            year=2026,
            venue="ICML",
            url="https://example.com/1b",
            keywords=["agents"],
        ),
        CollectedPaper(
            source_id="2",
            title="Vision Transformers",
            authors=["Grace"],
            abstract="Image classification",
            year=2026,
            venue="CVPR",
            url="https://example.com/2",
            keywords=["vision"],
        ),
        CollectedPaper(
            source_id="3",
            title="Retrieval Systems",
            authors=["Linus"],
            abstract="Ranking models",
            year=2026,
            venue="NeurIPS",
            url="https://example.com/3",
            keywords=["search"],
        ),
    ]

    result = collector.collect_from_papers(
        papers,
        topic="agent planning",
        venues=["ICML", "NeurIPS"],
    )

    assert [paper.source_id for paper in result] == ["1", "3"]


def test_paper_collector_returns_empty_for_blank_topic_without_match() -> None:
    collector = PaperCollector()

    result = collector.collect_from_papers(
        [
            CollectedPaper(
                source_id="4",
                title="General Research",
                authors=["Sam"],
                abstract="Broad topic",
                year=2026,
                venue="AAAI",
                url="https://example.com/4",
                keywords=[],
            )
        ],
        topic="",
        venues=["AAAI"],
    )

    assert [paper.source_id for paper in result] == ["4"]


def test_paper_collector_ignores_invalid_venues_and_normalizes_whitespace() -> None:
    collector = PaperCollector()

    result = collector.collect_from_papers(
        [
            CollectedPaper(
                source_id="5",
                title="Planning Agents",
                authors=["Ada"],
                abstract="Plan with agents",
                year=2026,
                venue="ICML",
                url="https://example.com/5",
                keywords=["agent"],
            )
        ],
        topic="agent",
        venues=["  ICML  ", None, 123, ""],
    )

    assert [paper.source_id for paper in result] == ["5"]
