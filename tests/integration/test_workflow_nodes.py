from __future__ import annotations

from app.services.analyzers.paper_analyzer import PaperAnalyzer
from app.services.collectors.base import CollectedPaper
from app.workflows.nodes import analyze_papers, collect_papers, run_trend_analysis
from app.workflows.progress import ProgressEvent
from app.workflows.state import ResearchState


def test_run_trend_analysis_writes_snapshot_back_to_state() -> None:
    state = ResearchState(
        topic="agent systems",
        papers=[
            CollectedPaper(
                source_id="p1",
                title="Agent Planning with Memory",
                authors=["Alice"],
                abstract="Planning and memory for agent workflows.",
                year=2024,
                venue="ICLR",
                url="https://example.com/p1",
                keywords=["Agent", "Memory", "Planning"],
            )
        ],
    )

    next_state = run_trend_analysis(state)

    assert next_state.trend_snapshot is not None
    assert next_state.trend_snapshot["hot_keywords"] == ["agent", "memory", "planning"]
    assert next_state.trend_snapshot["growth_signals"] == [{"year": 2024, "count": 1}]
    assert "共分析 1 篇论文" in next_state.trend_snapshot["summary"]


def test_collect_papers_preserves_explicit_empty_source_list() -> None:
    state = ResearchState(topic="agent systems", venues=["ICLR"])

    next_state = collect_papers(state, source_papers=[])

    assert next_state.papers == []


class _RecordingLLMClient:
    def generate_structured(self, *, prompt: str, schema: dict) -> dict:
        del prompt
        del schema
        return {
            "problem": "问题",
            "method": "方法",
            "innovation": "创新",
            "results": "结果",
            "limitations": "局限",
            "research_gap": "空白",
            "research_opportunity": "机会",
        }


def test_analyze_papers_emits_per_paper_progress_events() -> None:
    state = ResearchState(
        topic="agent systems",
        papers=[
            CollectedPaper(
                source_id="p1",
                title="Agent Planning with Memory",
                authors=["Alice"],
                abstract="Planning and memory for agent workflows.",
                year=2024,
                venue="ICLR",
                url="https://example.com/p1",
                keywords=["Agent", "Memory", "Planning"],
            ),
            CollectedPaper(
                source_id="p2",
                title="Agent Tool Use",
                authors=["Bob"],
                abstract="Tool use for agents.",
                year=2024,
                venue="NeurIPS",
                url="https://example.com/p2",
                keywords=["Agent", "Tools"],
            ),
        ],
    )
    events: list[ProgressEvent] = []

    analyze_papers(
        state,
        analyzer=PaperAnalyzer(_RecordingLLMClient()),
        progress_callback=events.append,
    )

    assert [event.status for event in events] == ["running", "running", "running", "completed"]
    assert [event.current for event in events] == [0, 1, 2, 2]
    assert [event.total for event in events] == [2, 2, 2, 2]
    assert events[0].stage_key == "analyze_papers"
    assert events[1].message == "正在分析论文 1/2"
    assert events[2].message == "正在分析论文 2/2"
    assert len(state.paper_analyses) == 2


def test_analyze_papers_emits_zero_progress_for_empty_input() -> None:
    state = ResearchState(topic="agent systems", papers=[])
    events: list[ProgressEvent] = []

    analyze_papers(
        state,
        analyzer=PaperAnalyzer(_RecordingLLMClient()),
        progress_callback=events.append,
    )

    assert [event.status for event in events] == ["running", "completed"]
    assert events[0].message == "未找到可分析论文"
    assert events[0].current == 0
    assert events[0].total == 0
    assert events[1].current == 0
    assert events[1].total == 0


def test_analyze_papers_respects_state_max_results() -> None:
    state = ResearchState(
        topic="agent systems",
        max_results=2,
        papers=[
            CollectedPaper(
                source_id="p1",
                title="Paper 1",
                authors=["Alice"],
                abstract="abstract 1",
                year=2024,
                venue="Nature",
                url="https://example.com/p1",
            ),
            CollectedPaper(
                source_id="p2",
                title="Paper 2",
                authors=["Bob"],
                abstract="abstract 2",
                year=2024,
                venue="Nature",
                url="https://example.com/p2",
            ),
            CollectedPaper(
                source_id="p3",
                title="Paper 3",
                authors=["Carol"],
                abstract="abstract 3",
                year=2024,
                venue="Nature",
                url="https://example.com/p3",
            ),
        ],
    )

    analyze_papers(state, analyzer=PaperAnalyzer(_RecordingLLMClient()))

    assert len(state.paper_analyses) == 2
