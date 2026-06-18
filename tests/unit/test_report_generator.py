from app.services.analyzers.paper_analyzer import PaperAnalysisResult
from app.services.collectors.base import CollectedPaper
from app.services.generators.report_generator import ReportGenerator


def test_report_generator_outputs_target_four_section_report() -> None:
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
                summary="本文提出分层规划框架，并结合记忆与工具反馈提升复杂任务表现。",
                problem="问题",
                method="方法",
                innovation="创新",
                results="结果",
                limitations="局限",
                research_gap="研究空白",
                research_opportunity="研究机会",
            )
        ],
    )

    for heading in [
        "# 研究报告",
        "## 一、研究概览",
        "## 二、重点论文解读",
        "## 三、研究机会",
        "## 四、推荐阅读",
    ]:
        assert heading in report
    assert "## 三、研究趋势分析" not in report
    assert "## 四、新兴研究方向" not in report
    assert "## 五、研究机会与空白" not in report
    assert "1. Agent Planning" in report
    assert "简要概述：本文提出分层规划框架，并结合记忆与工具反馈提升复杂任务表现。" in report
    assert "针对的问题：问题" in report
    assert "方法：方法" in report
    assert "创新点：创新" in report
    assert "结果：结果" in report
    assert "局限：局限" in report
    assert "1. 这些论文可利用/结合之处" in report
    assert "研究机会" in report
    assert "2. 这些论文尚未做好的地方" in report
    assert "研究空白" in report


def test_report_generator_handles_empty_inputs_without_crashing() -> None:
    generator = ReportGenerator()

    report = generator.generate(
        topic="AI Agent",
        papers=[],
        analyses=[],
    )

    assert "# 研究报告" in report
    assert "## 一、研究概览" in report
    assert "## 四、推荐阅读" in report
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
    )

    assert "1. Only Paper" in report
    assert "简要概述：Abstract" in report
    assert "针对的问题：问题1" in report
    assert "2. 未匹配论文" in report
    assert "针对的问题：问题2" in report
    assert "这些论文可利用/结合之处" in report
    assert "这些论文尚未做好的地方" in report


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
    )

    assert "Agent Planning（智能体规划）" in report


def test_report_generator_overview_marks_pdf_analysis_availability() -> None:
    generator = ReportGenerator()

    report = generator.generate(
        topic="AI Agent",
        papers=[
            CollectedPaper(
                source_id="1",
                title="PubMed Paper",
                authors=["Ada"],
                abstract="Abstract",
                year=2026,
                venue="Nature",
                url="https://pubmed.ncbi.nlm.nih.gov/1/",
                pdf_url="",
                keywords=["agent"],
            ),
            CollectedPaper(
                source_id="2",
                title="arXiv Paper",
                authors=["Turing"],
                abstract="Abstract",
                year=2026,
                venue="arXiv",
                url="https://arxiv.org/abs/2501.00001v1",
                pdf_url="https://arxiv.org/pdf/2501.00001v1.pdf",
                keywords=["agent"],
            ),
        ],
        analyses=[],
    )

    assert "PubMed Paper | PDF：无" in report
    assert "arXiv Paper | PDF：有" in report
